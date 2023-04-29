from __future__ import annotations
from paramiko import MissingHostKeyPolicy, SSHClient, SFTPClient
from worker.config import load_config
from collections.abc import Callable
from typing import Type, Any, ContextManager
from types import TracebackType
from sys import stdout, stderr
from os.path import dirname, basename
from time import sleep


class SSH(ContextManager["SSH"]):
    def __init__(self, client: SSHClient):
        self.__client = client
        self.__sftp = self.__client.open_sftp()

    def run(self, command: str, input: bytes = b"") -> int:
        def out(x: bytes) -> None:
            stdout.buffer.write(x)
            stdout.flush()

        def err(x: bytes) -> None:
            stderr.buffer.write(x)
            stderr.flush()

        return self.__run(command, out, err, input)

    def check_call(self, command: str, input: bytes = b"") -> None:
        result = self.run(command, input)
        if result != 0:
            raise Exception(result)

    def popen(self, command: str) -> None:
        self.__client.exec_command(command)

    def run_output(self, command: str, input: bytes = b"") -> tuple[int, bytes, bytes]:
        stdout = bytearray()
        stderr = bytearray()
        return (
            self.__run(
                command,
                lambda x: stdout.extend(x),
                lambda x: stderr.extend(x),
                input,
            ),
            bytes(stdout),
            bytes(stderr),
        )

    def __run(
        self,
        command: str,
        onout: Callable[[bytes], Any],
        onerr: Callable[[bytes], Any],
        input: bytes = b"",
    ) -> int:
        _, stdout, _ = self.__client.exec_command(command)
        channel = stdout.channel
        while input:
            input = input[channel.send(input) :]
        while True:
            exit = channel.exit_status_ready()
            while channel.recv_ready():
                recv = channel.recv(1024)
                if not recv:
                    break
                onout(recv)
            while channel.recv_stderr_ready():
                recv = channel.recv(1024)
                if not recv:
                    break
                onerr(recv)
            if exit:
                return channel.exit_status
            sleep(0.1)

    def close(self) -> None:
        self.__client.close()

    def __enter__(self) -> SSH:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        self.close()

    @property
    def sftp(self) -> SFTPClient:
        return self.__sftp

    def exists(self, path: str) -> bool:
        return basename(path) in self.__sftp.listdir(dirname(path))


def ssh_connect(ip: str | None = None, port: int | None = None) -> SSH:
    config = load_config()
    client = SSHClient()
    client.set_missing_host_key_policy(MissingHostKeyPolicy())
    client.connect(
        config["server"]["host"] if ip is None else ip,
        config["server"]["port"] if port is None else port,
        "root",
        config["server"]["password"],
        timeout=10,
    )
    return SSH(client)
