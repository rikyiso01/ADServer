from __future__ import annotations
from worker.scripts.setup_keys import setup_keys
from worker.ssh import ssh_connect, SSH
from worker.config import load_config, Config, get_config
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
            _ = copyfile("config.toml", f.name)
        _ = copyfile("tests/config.test.toml", "config.toml")
        load_config("config.toml").unwrap()
        yield get_config()
        _ = copyfile(f.name, "config.toml")


@fixture(scope="session")
def docker(test_config: Config) -> Iterable[Config]:
    _ = check_call(["docker", "compose", "down", "-v", "--remove-orphans"])
    _ = check_call(["docker", "compose", "up", "-d", "--build"])
    sleep(1)
    yield test_config
    _ = check_call(["docker", "compose", "logs"])
    _ = check_call(["docker", "compose", "down", "-v"])


@fixture(scope="session")
def remote_server(docker: Config) -> Iterable[SSH]:
    print("Before docker compose")
    _ = check_call(
        [
            "docker",
            "compose",
            "-f",
            "tests/docker-compose.yml",
            "down",
            "-v",
            "--remove-orphans",
        ]
    )
    _ = check_call(
        ["docker", "compose", "-f", "tests/docker-compose.yml", "up", "-d", "--build"]
    )
    sleep(1)
    setup_keys(
        "127.0.0.1",
        2222,
        skip_tools_install=False,
        skip_aliases=False,
        skip_keys=False,
        skip_private_key=False,
        skip_tcpdump=False,
        interface_ip="10.89.12.25",
        ssh_port=2222,
    )
    print("Setupped keys")
    sleep(6)
    with ssh_connect("127.0.0.1", 2222) as ssh:
        ssh = ssh.unwrap()
        yield ssh
    _ = check_call(
        ["docker", "compose", "-f", "tests/docker-compose.yml", "down", "-v"]
    )
