from __future__ import annotations
from os import makedirs, listdir, remove
from os.path import join, splitext
from time import sleep
from shutil import copyfileobj, copyfile
from gzip import open as gzip_open
from worker.config import (
    load_config,
    SERVER_DUMPS_FOLDER,
    COMPRESSED_FOLDER,
    UNCOMPRESSED_FOLDER,
    BACKUP_FOLDER,
    DATA_FOLDER,
)
from paramiko import SFTPClient
from paramiko.ssh_exception import NoValidConnectionsError
from worker.ssh import ssh_connect
from httpx import post
from typing import NoReturn
from signal import signal, SIGTERM
from sys import stderr
from socket import gaierror


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
        assert len(ssh.sftp.listdir(SERVER_DUMPS_FOLDER)) <= 2


def main() -> NoReturn:
    print("Main", flush=True)
    config = load_config()
    signal(SIGTERM, lambda _, __: exit())
    makedirs(COMPRESSED_FOLDER, exist_ok=True)
    makedirs(UNCOMPRESSED_FOLDER, exist_ok=True)
    makedirs(BACKUP_FOLDER, exist_ok=True)
    while True:
        print("looping", flush=True)
        try:
            with ssh_connect() as ssh:
                while not ssh.exists(SERVER_DUMPS_FOLDER):
                    print("Waiting for dumps folder creation", flush=True)
                    sleep(1)
                loop(ssh.sftp)
            sleep(config["tcpdumper"]["interval"])
        except (NoValidConnectionsError, gaierror, TimeoutError) as e:
            print(e, file=stderr, flush=True)
            sleep(1)


def loop(client: SFTPClient) -> None:
    rsync(client)
    extract_all()
    upload_all()


def rsync(client: SFTPClient) -> None:
    for name in client.listdir(SERVER_DUMPS_FOLDER):
        _, ext = splitext(name)
        if ext == ".gz":
            remote_file = join(SERVER_DUMPS_FOLDER, name)
            local_file = join(COMPRESSED_FOLDER, name)
            client.get(remote_file, local_file)
            client.remove(remote_file)


def extract_all():
    for name in listdir(COMPRESSED_FOLDER):
        source_file = join(COMPRESSED_FOLDER, name)
        target_file = join(UNCOMPRESSED_FOLDER, splitext(name)[0])
        gunzip(source_file, target_file)
        remove(source_file)


def gunzip(source_filepath: str, dest_filepath: str, block_size: int = 65536) -> None:
    with gzip_open(source_filepath, "rb") as s_file, open(
        dest_filepath, "wb"
    ) as d_file:
        copyfileobj(s_file, d_file, block_size)


def upload_all() -> None:
    for name in listdir(UNCOMPRESSED_FOLDER):
        file = join(UNCOMPRESSED_FOLDER, name)
        backup_file = join(BACKUP_FOLDER, name)
        post(
            "http://caronte:3333/api/pcap/file",
            json={"file": file, "flush_all": False, "delete_original_file": False},
        )
        copyfile(file, backup_file)
        remove(file)
