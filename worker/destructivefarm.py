from __future__ import annotations
from logging import getLogger
from pydantic import BaseModel
from os.path import join
from subprocess import call
from httpx import get
from worker.config import get_config, wait_for_host_ip


PYTHON_CONFIG = """CONFIG = {}"""
LOGGER = getLogger(__name__)


class DestructiveFarmConfig(BaseModel):
    TEAMS: dict[str, str]
    FLAG_FORMAT: str
    SUBMIT_FLAG_LIMIT: int
    SUBMIT_PERIOD: int
    FLAG_LIFETIME: int
    SERVER_PASSWORD: str
    ENABLE_API_AUTH: bool
    API_TOKEN: str


def generate_config(self_host: str | None = None) -> str:
    config = get_config()
    if self_host is None:
        self_host = wait_for_host_ip(config.server.host)
    teams = {
        f"Team #{i}": config.teams.format.format(i)
        for i in range(config.teams.min_team, config.teams.max_team + 1)
        if config.teams.format.format(i) != self_host
    }
    config_dict = DestructiveFarmConfig(
        TEAMS=teams,
        FLAG_FORMAT=config.flag.format,
        SUBMIT_FLAG_LIMIT=config.farm.flag.submit_flag_limit,
        SUBMIT_PERIOD=config.farm.flag.submit_period,
        FLAG_LIFETIME=config.farm.flag.flag_lifetime,
        SERVER_PASSWORD=config.farm.password,
        ENABLE_API_AUTH=config.farm.enable_api_auth,
        API_TOKEN=config.farm.api_token,
    )
    result = config_dict.model_dump()
    for key, value in config.farm.submit.items():
        result[key.upper()] = value
    LOGGER.debug(f"Generated config: {result}")
    return PYTHON_CONFIG.format(repr(result))


def destructivefarm() -> None:
    LOGGER.info("Writing destructive farm config")
    with open(join("server", "config.py"), "w") as f:
        _ = f.write(generate_config())
    LOGGER.info("Starting destructive farm process")
    exit(call(["./start_server.sh"], cwd="server"))


def destructivefarm_check() -> None:
    config = get_config()
    LOGGER.debug("Healthchecking destructive farm login")
    response = get("http://127.0.0.1:5000", auth=("admin", config.farm.password))
    if response.status_code != 200:
        LOGGER.warning(
            f"Healthchecking failed: status_code={response.status_code} text={response.text}"
        )
    assert response.status_code == 200
    actual = response.text
    if config.flag.format not in actual:
        LOGGER.warning(f"Healthchecking failed: text={response.text}")
    assert config.flag.format in actual
