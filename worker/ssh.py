from __future__ import annotations
from paramiko import MissingHostKeyPolicy, SSHClient, SFTPClient
from collections.abc import Callable
from typing import Type, Any, ContextManager
from types import TracebackType
from sys import stdout, stderr
from time import sleep
from worker.config import CONFIG
from logging import getLogger


class SSH(ContextManager["SSH"]):
    __logger = getLogger("ssh.SSH")

    def __init__(
        self,
        client: SSHClient,
        /,
        *,
        print_command_info: tuple[str, str, int] | None = None,
    ):
        self.__client = client
        self.__sftp = self.__client.open_sftp()
        self.__print_command_info = print_command_info

    def print_command(self, cmd: str):
        if self.__print_command_info is not None:
            user, host, port = self.__print_command_info
            print(f"[{user}@{host}:{port}]# {cmd}")

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
        self.print_command(command)
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
        self.print_command(command)
        SSH.__logger.debug(f"Exec ssh command {command}")
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

    def put(self, localpath: str, remotepath: str):
        if self.__print_command_info is not None:
            user, host, port = self.__print_command_info
            print(f"$ scp -P {port} {localpath} {user}@{host}:{remotepath}")
        SSH.__logger.debug(f"Uploading file from {localpath} to {remotepath}")
        self.__sftp.put(localpath, remotepath)

    @property
    def sftp(self) -> SFTPClient:
        return self.__sftp

    def exists(self, path: str) -> bool:
        return self.run(f"[ -e '{path}' ]") == 0


def ssh_connect(
    ip: str | None = None, port: int | None = None, /, *, print_commands: bool = False
) -> SSH:
    logger = getLogger("ssh.ssh_connect")
    client = SSHClient()
    client.set_missing_host_key_policy(MissingHostKeyPolicy())
    ip = CONFIG["server"]["host"] if ip is None else ip
    port = CONFIG["server"]["port"] if port is None else port
    user = "root"
    logger.debug(f"Opening ssh connection to {user}@{ip}:{port}")
    client.connect(
        ip,
        port,
        user,
        CONFIG["server"]["password"],
        timeout=10,
    )
    return SSH(client, print_command_info=(user, ip, port) if print_commands else None)
