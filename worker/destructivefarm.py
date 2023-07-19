from __future__ import annotations
from worker.config import get_host_ip, CONFIG
from os.path import join
from subprocess import Popen
from signal import signal, SIGTERM
from httpx import get
from logging import getLogger

PYTHON_CONFIG = """
CONFIG = {{
    "TEAMS": {teams},
    "FLAG_FORMAT": r"{flag}",
    {system},
    "SUBMIT_FLAG_LIMIT": {flag_limit},
    "SUBMIT_PERIOD": {period},
    "FLAG_LIFETIME": {lifetime},
    "SERVER_PASSWORD": "{password}",
    "ENABLE_API_AUTH": {api},
    "API_TOKEN": "{token}",
}}
"""


def generate_config(self_host: str | None = None) -> str:
    logger = getLogger("destructivefarm.generate_config")
    if self_host is None:
        self_host = get_host_ip(CONFIG["server"]["host"])
    teams = CONFIG["teams"]
    flag = CONFIG["flag"]
    farm = CONFIG["farm"]
    farm_flag = farm["flag"]
    teams_dict = {
        f"Team #{i}": teams["format"].format(i)
        for i in range(teams["min_team"], teams["max_team"] + 1)
        if teams["format"].format(i) != self_host
    }
    result = PYTHON_CONFIG.format(
        teams=repr(teams_dict),
        flag=flag["format"],
        system=",\n    ".join(
            f'"{key.upper()}":{repr(value)}' for key, value in farm["submit"].items()
        ),
        flag_limit=farm_flag["submit_flag_limit"],
        period=farm_flag["submit_period"],
        lifetime=farm_flag["flag_lifetime"],
        password=farm["password"],
        api=farm["enable_api_auth"],
        token=farm["api_token"],
    )
    logger.debug(f"Generated config: {result}")
    return result


def main() -> None:
    logger = getLogger("destructivefarm")
    logger.info("Writing destructive farm config")
    with open(join("server", "config.py"), "w") as f:
        f.write(generate_config())
    logger.info("Starting destructive farm process")
    process = Popen(["./start_server.sh"], cwd="server")
    logger.debug("Registering SIGTERM signal")
    signal(SIGTERM, lambda _, __: process.kill())
    exit_code = process.wait()
    if exit_code == 0:
        logger.info("Destructive Farm exited successfully")
    else:
        logger.critical(f"Destructive Farm exited with non 0 exit code: {exit_code}")
    exit(exit_code)


def healthcheck() -> None:
    logger = getLogger("destructivefarm.healthcheck")
    logger.debug("Healthchecking destructive farm login")
    response = get("http://127.0.0.1:5000", auth=("admin", CONFIG["farm"]["password"]))
    if response.status_code != 200:
        logger.warning(
            f"Healthchecking failed: status_code={response.status_code} text={response.text}"
        )
    assert response.status_code == 200
    actual = response.text
    if CONFIG["flag"]["format"] not in actual:
        logger.warning(f"Healthchecking failed: text={response.text}")
    assert CONFIG["flag"]["format"] in actual
