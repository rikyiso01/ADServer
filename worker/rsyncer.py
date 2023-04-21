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
)
from paramiko import SFTPClient
from paramiko.ssh_exception import NoValidConnectionsError
from worker.ssh import ssh_connect
from httpx import post
from typing import NoReturn
from signal import signal, SIGTERM
from sys import stderr
from socket import gaierror


def healthcheck(ip: str | None = None, port: int | None = None) -> None:
    print("connecting", flush=True)
    with ssh_connect(ip, port) as ssh:
        print("connected", flush=True)
        result = ssh.run("pgrep tcpdump")
        assert result == 0


def main() -> NoReturn:
    print("Main", flush=True)
    config = load_config()
    signal(SIGTERM, lambda _, __: exit())
    while True:
        try:
            with ssh_connect() as ssh:
                print("Executing pkill", flush=True)
                ssh.run("pkill tcpdump")
                print("Making dir", flush=True)
                if not ssh.exists(SERVER_DUMPS_FOLDER):
                    ssh.sftp.mkdir(SERVER_DUMPS_FOLDER)
                makedirs(COMPRESSED_FOLDER, exist_ok=True)
                makedirs(UNCOMPRESSED_FOLDER, exist_ok=True)
                makedirs(BACKUP_FOLDER, exist_ok=True)
                print("Executing tcpdump", flush=True)
                while ssh.run("command -v tcpdump") != 0:
                    print(
                        "Waiting for tcpdump to be installed", file=stderr, flush=True
                    )
                    sleep(1)
                ssh.popen(
                    f"tcpdump -w '{SERVER_DUMPS_FOLDER}/%H-%M-%S.pcap' -G {config['tcpdumper']['interval']} -Z root -i '{config['tcpdumper']['interface']}' -z gzip not port {config['server']['port']} > /dev/null 2> /dev/null",
                )
            break
        except NoValidConnectionsError as e:
            print(e, file=stderr, flush=True)
        except gaierror as e:
            print(e, file=stderr, flush=True)
        except TimeoutError as e:
            print(e, file=stderr, flush=True)
        sleep(1)
    while True:
        print("looping", flush=True)
        with ssh_connect() as ssh:
            loop(ssh.sftp)
        sleep(config["tcpdumper"]["interval"])


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
