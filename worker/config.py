from __future__ import annotations
from typing import TypedDict, Any, cast
from toml import load
from os.path import join
from httpx import get

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
        url = GITHUB_KEYS_URL.format(user)
        keys: list[GithubUserKey] = get(url).json()
        for key in keys:
            result.append(key["key"])
    return result


class GithubUserKey(TypedDict):
    id: int
    key: str


def get_aliases(aliases: dict[str, str]) -> str:
    assert all("'" not in key for key in aliases)
    assert all('"' not in key for key in aliases)
    assert all("'" not in value for value in aliases.values())
    assert all('"' not in value for value in aliases.values())
    return "\n".join(f"alias {key}='{value}'" for key, value in aliases.items())
