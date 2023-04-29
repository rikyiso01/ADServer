from __future__ import annotations
from typing import TypedDict, Any, cast
from toml import load
from os.path import join
from httpx import get
from socket import gethostbyname, gaierror
from sys import stderr
from time import sleep

DATA_FOLDER = join("/", "data")
UNCOMPRESSED_FOLDER = join(DATA_FOLDER, "uncompressed")
BACKUP_FOLDER = join(DATA_FOLDER, "backup")
COMPRESSED_FOLDER = join(DATA_FOLDER, "compressed")

SERVER_DUMPS_FOLDER = join("/", "root", "dumps")

GITHUB_KEYS_URL = "https://api.github.com/users/{}/keys"


class Config(TypedDict):
    teams: Teams
    flag: Flag
    farm: Farm
    server: Server
    tcpdumper: TcpDumper
    git: Git
    sshkeys: SSHKeys
    aliases: dict[str, str]


class Teams(TypedDict):
    format: str
    min_team: int
    max_team: int


class Flag(TypedDict):
    format: str


class Farm(TypedDict):
    password: str
    enable_api_auth: bool
    api_token: str
    submit: dict[str, Any]
    flag: FarmFlag


class FarmFlag(TypedDict):
    submit_flag_limit: int
    submit_period: int
    flag_lifetime: int


class Server(TypedDict):
    host: str
    port: int
    password: str


class TcpDumper(TypedDict):
    interface: str
    interval: int


class Git(TypedDict):
    git_repo: str
    ssh_key: str


class SSHKeys(TypedDict):
    github_users: list[str]


def load_config() -> Config:
    return cast(Config, load("config.toml"))


def get_git_host(repo: str) -> str:
    return repo[repo.index("@") + 1 : repo.index(":")]


def get_ssh_keys(github_users: list[str]) -> list[str]:
    result: list[str] = []
    for user in github_users:
        result.extend(get_ssh_key(user))
    return result


def get_ssh_key(github_user: str) -> list[str]:
    result: list[str] = []
    url = GITHUB_KEYS_URL.format(github_user)
    keys: list[GithubUserKey] = get(url).json()
    for key in keys:
        result.append(key["key"])
    return result


class GithubUserKey(TypedDict):
    id: int
    key: str


def escape_shell(command: str) -> str:
    return command.replace("\\", "\\\\").replace("$", "\\$").replace('"', '\\"')


def get_host_ip(host: str) -> str:
    while True:
        try:
            return gethostbyname(host)
        except gaierror as e:
            print(e, file=stderr, flush=True)
        sleep(1)
