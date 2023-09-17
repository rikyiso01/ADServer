from __future__ import annotations
from logging import getLogger
from paramiko import MissingHostKeyPolicy, SSHClient, SFTPClient, SSHException
from collections.abc import Callable, Generator
from typing import Any
from sys import stdout, stderr
from time import sleep
from contextlib import contextmanager
from attrs import frozen
from functools import cached_property
from result import Err, Ok, Result
from subprocess import SubprocessError
from worker.config import get_config

SSHError = SSHException | OSError
SSH_ERROR = (SSHException, OSError)
LOGGER = getLogger(__name__)


@frozen(slots=False)
class SSH:
    _client: SSHClient
    _print_command_info: tuple[str, str, int] | None = None

    @cached_property
    def _sftp(self) -> SFTPClient:
        return self._client.open_sftp()

    def print_command(self, cmd: str) -> None:
        if self._print_command_info is not None:
            user, host, port = self._print_command_info
            print(f"[{user}@{host}:{port}]# {cmd}")

    def call(self, command: str, input: bytes = b"") -> Result[int, SSHError]:
        def out(x: bytes) -> None:
            _ = stdout.buffer.write(x)
            stdout.flush()

        def err(x: bytes) -> None:
            _ = stderr.buffer.write(x)
            stderr.flush()

        return self.__run(command, out, err, input)

    def check_call(
        self, command: str, input: bytes = b""
    ) -> Result[None, SSHError | SubprocessError]:
        result = self.call(command, input)
        if isinstance(result, Err):
            return result
        if result.ok_value != 0:
            return Err(SubprocessError(result.ok_value))
        return Ok(None)

    def popen(self, command: str) -> Result[None, SSHError]:
        self.print_command(command)
        try:
            _ = self._client.exec_command(command)
        except SSH_ERROR as e:
            return Err(e)
        return Ok(None)

    def run(
        self, command: str, input: bytes = b""
    ) -> Result[tuple[int, bytes, bytes], SSHError]:
        stdout = bytearray()
        stderr = bytearray()
        result = self.__run(
            command,
            lambda x: stdout.extend(x),
            lambda x: stderr.extend(x),
            input,
        )
        if isinstance(result, Err):
            return result
        return Ok((result.ok_value, bytes(stdout), bytes(stderr)))

    def __run(
        self,
        command: str,
        onout: Callable[[bytes], Any],
        onerr: Callable[[bytes], Any],
        input: bytes = b"",
    ) -> Result[int, SSHError]:
        self.print_command(command)
        LOGGER.debug(f"Exec ssh command {command}")
        try:
            _, stdout, _ = self._client.exec_command(command)
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
                    return Ok(channel.exit_status)
                sleep(0.1)
        except SSH_ERROR as e:
            return Err(e)

    def put(self, localpath: str, remotepath: str) -> Result[None, SSHError]:
        if self._print_command_info is not None:
            user, host, port = self._print_command_info
            print(f"$ scp -P {port} {localpath} {user}@{host}:{remotepath}")
        LOGGER.debug(f"Uploading file from {localpath} to {remotepath}")
        try:
            _ = self._sftp.put(localpath, remotepath)
        except SSH_ERROR as e:
            return Err(e)
        return Ok(None)

    def listdir(self, path: str) -> Result[list[str], SSHError]:
        try:
            return Ok(self._sftp.listdir(path))
        except SSH_ERROR as e:
            return Err(e)

    def get(self, remote_path: str, local_path: str) -> Result[None, SSHError]:
        try:
            self._sftp.get(remote_path, local_path)
        except SSH_ERROR as e:
            return Err(e)
        return Ok(None)

    def remove(self, remote_path: str) -> Result[None, SSHError]:
        try:
            self._sftp.remove(remote_path)
        except SSH_ERROR as e:
            return Err(e)
        return Ok(None)

    def exists(self, path: str) -> Result[bool, SSHError]:
        result = self.call(f"[ -e '{path}' ]")
        if isinstance(result, Err):
            return result
        return Ok(result.ok_value == 0)


@contextmanager
def ssh_connect(
    ip: str | None = None,
    port: int | None = None,
    /,
    *,
    print_commands: bool = False,
) -> Generator[Result[SSH, SSHError], None, None]:
    config = get_config()
    ip = config.server.host if ip is None else ip
    port = config.server.port if port is None else port
    user = "root"
    LOGGER.debug(f"Opening ssh connection to {user}@{ip}:{port}")
    with SSHClient() as client:
        client.set_missing_host_key_policy(MissingHostKeyPolicy())
        try:
            client.connect(ip, port, user, config.server.password, timeout=10)
        except SSH_ERROR as exception:
            yield Err(exception)
            return
        ssh = SSH(client, (user, ip, port) if print_commands else None)
        yield Ok(ssh)
