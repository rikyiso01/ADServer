from __future__ import annotations
from os import makedirs, listdir, remove
from os.path import exists, join, splitext
from time import sleep
from shutil import copyfile, copyfileobj
from gzip import open as gzip_open
from httpx import post

from result import Err, Ok, Result
from worker.config import (
    COMPRESSED_FOLDER,
    UNCOMPRESSED_FOLDER,
    BACKUP_FOLDER,
    DATA_FOLDER,
    NETWORK_ATTEMPTS_INTERVAL,
    get_config,
)
from worker.ssh import SSH, ssh_connect, SSHError
from typing import NoReturn, Optional
from logging import getLogger

LOGGER = getLogger()


def worker_check(
    ip: Optional[str] = None,
    port: Optional[int] = None,
    data_folder: str = DATA_FOLDER,
) -> None:
    config = get_config()
    with ssh_connect(ip, port) as result:
        ssh = result.unwrap()
        assert ssh.check_call("pgrep tcpdump").is_ok()
        assert len(ssh.listdir(config.tcpdumper.dumps_folder).unwrap()) <= 2
    compressed = listdir(join(data_folder, "compressed"))
    uncompressed = listdir(join(data_folder, "uncompressed"))
    backups = listdir(join(data_folder, "backup"))
    assert len(compressed) <= 1
    assert len(uncompressed) <= 1
    assert len(backups) >= 1
    for name in compressed:
        assert splitext(name)[1] == ".gz"
    for name in uncompressed:
        assert splitext(name)[1] == ".pcap"
    for name in backups:
        assert splitext(name)[1] == ".pcap"


def worker() -> NoReturn:
    config = get_config()
    LOGGER.debug("Creating local dumps folders")
    makedirs(COMPRESSED_FOLDER, exist_ok=True)
    makedirs(UNCOMPRESSED_FOLDER, exist_ok=True)
    makedirs(BACKUP_FOLDER, exist_ok=True)
    while True:
        LOGGER.info("Starting worker loop")
        with ssh_connect() as result:
            if isinstance(result, Err):
                LOGGER.error(
                    f"Error connecting to the vulnbox, retrying in {NETWORK_ATTEMPTS_INTERVAL} seconds: {result.err_value}",
                )
                sleep(NETWORK_ATTEMPTS_INTERVAL)
                continue
            ssh = result.ok_value
            while not ssh.exists(config.tcpdumper.dumps_folder).unwrap():
                LOGGER.warning(f"Missing server dumps folder, waiting for its creation")
                sleep(1)
            loop(ssh)
        LOGGER.debug(f"Sleeping for {config.tcpdumper.interval} seconds")
        sleep(config.tcpdumper.interval)


def loop(client: SSH) -> None:
    LOGGER.debug("Starting rsync")
    result = rsync(client)
    if isinstance(result, Err):
        LOGGER.warning(
            f"Connection dropped while downloading pcaps: {result.err_value}"
        )
    LOGGER.debug("Starting extract_all")
    extract_all()
    upload_all()


def rsync(client: SSH) -> Result[None, SSHError]:
    config = get_config()
    result = client.listdir(config.tcpdumper.dumps_folder)
    if isinstance(result, Err):
        if isinstance(result.err_value, FileNotFoundError):
            raise result.err_value
        return result
    for name in result.ok_value:
        _, ext = splitext(name)
        if ext == ".gz":
            remote_file = join(config.tcpdumper.dumps_folder, name)
            local_file = join(COMPRESSED_FOLDER, name)
            LOGGER.debug(f"Starting download of file {name}")
            result = client.get(remote_file, local_file)
            if isinstance(result, Err):
                if exists(local_file):
                    remove(local_file)
                return result
            LOGGER.debug("Removing remote file")
            result = client.remove(remote_file)
            if isinstance(result, Err):
                if exists(local_file):
                    remove(local_file)
                return result
        else:
            LOGGER.debug(f"Skipping download of file {name}")
    return Ok(None)


def extract_all():
    for name in listdir(COMPRESSED_FOLDER):
        source_file = join(COMPRESSED_FOLDER, name)
        target_file = join(UNCOMPRESSED_FOLDER, splitext(name)[0])
        LOGGER.debug(f"Extracting file {name}")
        gunzip(source_file, target_file)
        LOGGER.debug(f"Removing file {name}")
        remove(source_file)


def gunzip(source_filepath: str, dest_filepath: str, block_size: int = 65536) -> None:
    with gzip_open(source_filepath, "rb") as s_file, open(
        dest_filepath, "wb"
    ) as d_file:
        copyfileobj(s_file, d_file, block_size)


def upload_all() -> None:
    config = get_config()
    for name in listdir(UNCOMPRESSED_FOLDER):
        file = join(UNCOMPRESSED_FOLDER, name)
        backup_file = join(BACKUP_FOLDER, name)
        LOGGER.debug(f"Uploading file {name}")
        response = post(
            "http://caronte:3333/api/pcap/file",
            json={"file": file, "flush_all": False, "delete_original_file": False},
            auth=(config.caronte.username, config.caronte.password),
        )
        if response.status_code != 202:
            LOGGER.error(
                f"Caronte upload responded with non 202 http code: {response.status_code} {response.text}"
            )
            response.raise_for_status()
            assert False
        LOGGER.debug(f"Backing up file before removal")
        _ = copyfile(file, backup_file)
        remove(file)
