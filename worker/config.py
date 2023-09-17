from __future__ import annotations
from typing import Any, Dict, List
from result import Err, Ok, Result
from toml import load
from os.path import join
from httpx import get, HTTPStatusError, RequestError
from socket import gethostbyname, gaierror
from time import sleep
from logging import getLogger
from pydantic import BaseModel, TypeAdapter, ValidationError
from json import JSONDecodeError
from worker.utils import no_extra

LOGGER = getLogger(__name__)
DATA_FOLDER = join("/", "data")
UNCOMPRESSED_FOLDER = join(DATA_FOLDER, "uncompressed")
BACKUP_FOLDER = join(DATA_FOLDER, "backup")
COMPRESSED_FOLDER = join(DATA_FOLDER, "compressed")

GITHUB_KEYS_URL = "https://api.github.com/users/{}/keys"

NETWORK_ATTEMPTS_INTERVAL = 1

config: Config | None = None


def get_config() -> Config:
    assert config is not None
    return config


def load_config(config_path: str) -> Result[None, ValidationError]:
    global config
    raw_config = load(config_path)
    try:
        config = Config.model_validate(raw_config)
    except ValidationError as e:
        return Err(e)
    return Ok(None)


@no_extra
class Config(BaseModel):
    teams: Teams
    flag: Flag
    caronte: Caronte
    farm: Farm
    server: Server
    tcpdumper: TcpDumper
    git: Git
    sshkeys: SSHKeys
    aliases: Dict[str, str]


@no_extra
class Teams(BaseModel):
    format: str
    min_team: int
    max_team: int


@no_extra
class Flag(BaseModel):
    format: str


@no_extra
class Caronte(BaseModel):
    username: str
    password: str


@no_extra
class Farm(BaseModel):
    password: str
    enable_api_auth: bool
    api_token: str
    submit: Dict[str, Any]
    flag: FarmFlag


@no_extra
class FarmFlag(BaseModel):
    submit_flag_limit: int
    submit_period: int
    flag_lifetime: int


@no_extra
class Server(BaseModel):
    host: str
    port: int
    password: str


@no_extra
class TcpDumper(BaseModel):
    interval: int
    dumps_folder: str


@no_extra
class Git(BaseModel):
    git_repo: str
    ssh_key: str


@no_extra
class SSHKeys(BaseModel):
    github_users: List[str]


class InvalidHost(Exception):
    ...


def get_git_host(repo: str) -> Result[str, InvalidHost]:
    start = repo.find("@")
    end = repo.find(":")
    if start == -1 or end == -1:
        return Err(InvalidHost())
    return Ok(repo[start + 1 : end])


def get_ssh_keys(github_users: list[str]) -> Result[list[str], GithubApiError]:
    result: list[str] = []
    for user in github_users:
        res = get_ssh_key(user)
        if isinstance(res, Err):
            return res
        result.extend(res.ok_value)
    return Ok(result)


def get_ssh_key(
    github_user: str,
) -> Result[list[str], GithubApiError]:
    result: list[str] = []
    url = GITHUB_KEYS_URL.format(github_user)
    LOGGER.debug(f"Getting ssh key of user {github_user}")
    try:
        response = get(url)
    except RequestError as e:
        return Err(e)
    try:
        response.raise_for_status()
    except HTTPStatusError as e:
        LOGGER.error(
            f"Github responded with non 200 status code: {response.status_code} {response.text}"
        )
        return Err(e)
    try:
        json = response.json()
    except JSONDecodeError as e:
        return Err(e)
    try:
        keys = TypeAdapter(list[GithubUserKey]).validate_python(json)
    except ValidationError as e:
        return Err(e)
    LOGGER.debug(f"Found {len(keys)} keys for user {github_user}")
    for key in keys:
        result.append(key.key)
    return Ok(result)


class GithubUserKey(BaseModel):
    id: int
    key: str


GithubApiError = HTTPStatusError | RequestError | ValidationError | JSONDecodeError


def getaddrinfo(host: str) -> Result[str, OSError]:
    LOGGER.debug(f"Resolving {host}")
    try:
        result = gethostbyname(host)
    except gaierror as e:
        return Err(e)
    LOGGER.debug(f"Resolved host with {result}")
    return Ok(result)


def wait_for_host_ip(host: str) -> str:
    while True:
        match getaddrinfo(host):
            case Ok(value):
                return value
            case Err(e):
                LOGGER.error(
                    f"Error getting address info of {host}, retrying in {NETWORK_ATTEMPTS_INTERVAL} seconds: {e}",
                )
                sleep(NETWORK_ATTEMPTS_INTERVAL)
