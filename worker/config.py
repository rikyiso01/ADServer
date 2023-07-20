from __future__ import annotations
from typing import Any, cast, Dict, List
from toml import load
from os.path import join
from httpx import get
from socket import gethostbyname, gaierror
from time import sleep
from logging import getLogger
from typing_extensions import TypedDict
from pydantic import TypeAdapter, ConfigDict

DATA_FOLDER = join("/", "data")
UNCOMPRESSED_FOLDER = join(DATA_FOLDER, "uncompressed")
BACKUP_FOLDER = join(DATA_FOLDER, "backup")
COMPRESSED_FOLDER = join(DATA_FOLDER, "compressed")

GITHUB_KEYS_URL = "https://api.github.com/users/{}/keys"

NETWORK_ATTEMPTS_INTERVAL = 1

CONFIG = cast("Config", {})


def load_config(config_path: str):
    config: dict[str, object] = cast("dict[str, object]", CONFIG)
    config.clear()
    new_config = load(config_path)
    adapter = TypeAdapter(Config)
    adapter.validate_python(new_config, strict=True)
    config.update(new_config)


class Config(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    teams: Teams
    flag: Flag
    caronte: Caronte
    farm: Farm
    server: Server
    tcpdumper: TcpDumper
    git: Git
    sshkeys: SSHKeys
    aliases: Dict[str, str]


class Teams(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore

    format: str
    min_team: int
    max_team: int


class Flag(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    format: str


class Caronte(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    username: str
    password: str


class Farm(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    password: str
    enable_api_auth: bool
    api_token: str
    submit: Dict[str, Any]
    flag: FarmFlag


class FarmFlag(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    submit_flag_limit: int
    submit_period: int
    flag_lifetime: int


class Server(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    host: str
    port: int
    password: str


class TcpDumper(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    interval: int
    dumps_folder: str


class Git(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    git_repo: str
    ssh_key: str


class SSHKeys(TypedDict):
    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore
    github_users: List[str]


def get_git_host(repo: str) -> str:
    return repo[repo.index("@") + 1 : repo.index(":")]


def get_ssh_keys(github_users: list[str]) -> list[str]:
    result: list[str] = []
    for user in github_users:
        result.extend(get_ssh_key(user))
    return result


class JsonParseError(Exception):
    ...


def get_ssh_key(github_user: str) -> list[str]:
    logger = getLogger("get_ssh_key")
    result: list[str] = []
    url = GITHUB_KEYS_URL.format(github_user)
    logger.debug(f"Getting ssh key of user {github_user}")
    response = get(url)
    if response.status_code != 200:
        logger.error(
            f"Github responded with non 200 status code: {response.status_code} {response.text}"
        )
    response.raise_for_status()
    json = response.json()
    try:
        if not isinstance(json, list):
            raise JsonParseError()
        keys: list[GithubUserKey] = json
        logger.debug(f"Found {len(keys)} keys for user {github_user}")
        for key in keys:
            if not isinstance(key, dict):  # type: ignore
                raise JsonParseError()
            if "key" not in key:
                raise JsonParseError()
            result.append(key["key"])
        return result
    except JsonParseError:
        logger.error(f"Github responded with an invalid json: {json}")
        raise


class GithubUserKey(TypedDict):
    id: int
    key: str


def escape_shell(command: str) -> str:
    return command.replace("\\", "\\\\").replace("$", "\\$").replace('"', '\\"')


def get_host_ip(host: str) -> str:
    logger = getLogger("get_host_ip")
    while True:
        logger.debug(f"Resolving {host}")
        try:
            result = gethostbyname(host)
            logger.debug(f"Resolved host with {result}")
            return result
        except gaierror as e:
            logger.error(
                f"Error getting address info of {host}, retrying in {NETWORK_ATTEMPTS_INTERVAL} seconds: {e}",
            )
        sleep(NETWORK_ATTEMPTS_INTERVAL)
