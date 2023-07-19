from __future__ import annotations
from os import makedirs, listdir, remove
from os.path import join, splitext
from time import sleep
from shutil import copyfileobj, copyfile
from gzip import open as gzip_open
from worker.config import (
    COMPRESSED_FOLDER,
    UNCOMPRESSED_FOLDER,
    BACKUP_FOLDER,
    DATA_FOLDER,
    NETWORK_ATTEMPTS_INTERVAL,
    CONFIG,
)
from paramiko import SFTPClient
from paramiko.ssh_exception import NoValidConnectionsError
from worker.ssh import ssh_connect
from httpx import post
from typing import NoReturn
from signal import signal, SIGTERM
from socket import gaierror
from logging import getLogger


def healthcheck(
    ip: str | None = None, port: int | None = None, data_folder: str = DATA_FOLDER
) -> None:
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
    with ssh_connect(ip, port) as ssh:
        assert ssh.run("pgrep tcpdump") == 0
        assert len(ssh.sftp.listdir(CONFIG["tcpdumper"]["dumps_folder"])) <= 2


def main() -> NoReturn:
    logger = getLogger("worker")
    logger.debug("Adding SIGTERM signal handler")
    signal(SIGTERM, lambda _, __: exit())
    logger.debug("Creating local dumps folders")
    makedirs(COMPRESSED_FOLDER, exist_ok=True)
    makedirs(UNCOMPRESSED_FOLDER, exist_ok=True)
    makedirs(BACKUP_FOLDER, exist_ok=True)
    while True:
        logger.info("Starting worker loop")
        try:
            with ssh_connect() as ssh:
                while not ssh.exists(CONFIG["tcpdumper"]["dumps_folder"]):
                    logger.warning(
                        f"Missing server dumps folder, waiting for its creation"
                    )
                    sleep(1)
                loop(ssh.sftp)
        except (NoValidConnectionsError, gaierror, TimeoutError) as e:
            logger.error(
                f"Error connecting to the vulnbox, retrying in {NETWORK_ATTEMPTS_INTERVAL} seconds: {e}",
            )
            sleep(NETWORK_ATTEMPTS_INTERVAL)
            continue
        logger.debug(f"Sleeping for {CONFIG['tcpdumper']['interval']} seconds")
        sleep(CONFIG["tcpdumper"]["interval"])


def loop(client: SFTPClient) -> None:
    logger = getLogger("worker.loop")
    logger.debug("Starting rsync")
    rsync(client)
    logger.debug("Starting extract_all")
    extract_all()
    logger.debug("Starting upload_all")
    upload_all()


def rsync(client: SFTPClient) -> None:
    logger = getLogger("worker.loop.rsync")
    for name in client.listdir(CONFIG["tcpdumper"]["dumps_folder"]):
        _, ext = splitext(name)
        if ext == ".gz":
            remote_file = join(CONFIG["tcpdumper"]["dumps_folder"], name)
            local_file = join(COMPRESSED_FOLDER, name)
            logger.debug(f"Starting download of file {name}")
            client.get(remote_file, local_file)
            logger.debug("Removing remote file")
            client.remove(remote_file)
        else:
            logger.debug(f"Skipping download of file {name}")


def extract_all():
    logger = getLogger("worker.loop.extract_all")
    for name in listdir(COMPRESSED_FOLDER):
        source_file = join(COMPRESSED_FOLDER, name)
        target_file = join(UNCOMPRESSED_FOLDER, splitext(name)[0])
        logger.debug(f"Extracting file {name}")
        gunzip(source_file, target_file)
        logger.debug(f"Removing file {name}")
        remove(source_file)


def gunzip(source_filepath: str, dest_filepath: str, block_size: int = 65536) -> None:
    with gzip_open(source_filepath, "rb") as s_file, open(
        dest_filepath, "wb"
    ) as d_file:
        copyfileobj(s_file, d_file, block_size)


def upload_all() -> None:
    logger = getLogger("worker.loop.upload_all")
    for name in listdir(UNCOMPRESSED_FOLDER):
        file = join(UNCOMPRESSED_FOLDER, name)
        backup_file = join(BACKUP_FOLDER, name)
        logger.debug(f"Uploading file {name}")
        response = post(
            "http://caronte:3333/api/pcap/file",
            json={"file": file, "flush_all": False, "delete_original_file": False},
        )
        response.raise_for_status()
        logger.debug(f"Backing up file before removal")
        copyfile(file, backup_file)
        remove(file)
