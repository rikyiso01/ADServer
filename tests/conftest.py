from __future__ import annotations
from worker.config import load_config, Config
from worker.scripts import setup_keys
from worker.ssh import ssh_connect, SSH
from pytest import fixture
from collections.abc import Iterable
from os.path import exists
from subprocess import check_call
from time import sleep
from shutil import copyfile
from tempfile import NamedTemporaryFile


@fixture(scope="session")
def test_config() -> Iterable[Config]:
    with NamedTemporaryFile("w") as f:
        if exists("config.toml"):
            copyfile("config.toml", f.name)
        copyfile("tests/config.test.toml", "config.toml")
        yield load_config()
        copyfile(f.name, "config.toml")


@fixture(scope="session")
def docker(test_config: Config) -> Iterable[Config]:
    check_call(["docker", "compose", "down", "-v"])
    check_call(["docker", "compose", "up", "-d", "--build"])
    sleep(1)
    yield test_config
    check_call(["docker", "compose", "logs"])
    check_call(["docker", "compose", "down", "-v"])


@fixture(scope="session")
def remote_server(docker: Config) -> Iterable[SSH]:
    print("before docker compose")
    check_call(["docker", "compose", "-f", "tests/docker-compose.yml", "down", "-v"])
    check_call(
        ["docker", "compose", "-f", "tests/docker-compose.yml", "up", "-d", "--build"]
    )
    sleep(1)
    setup_keys("127.0.0.1", 2222)
    print("setupped keys")
    sleep(6)
    with ssh_connect("127.0.0.1", 2222) as ssh:
        yield ssh
    check_call(["docker", "compose", "-f", "tests/docker-compose.yml", "down", "-v"])
