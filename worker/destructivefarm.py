from __future__ import annotations
from worker.config import load_config
from os.path import join
from subprocess import Popen
from signal import signal, SIGTERM
from httpx import get

CONFIG = """
CONFIG = {{
    "TEAMS": {{f"Team #{{i}}": "{teams}".format(i) for i in range({min_team},{max_team}+1) if i!={self_team}}},
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


def generate_config() -> str:
    config = load_config()
    teams = config["teams"]
    flag = config["flag"]
    farm = config["farm"]
    farm_flag = farm["flag"]
    return CONFIG.format(
        teams=teams["format"],
        max_team=teams["max_team"],
        min_team=teams["min_team"],
        self_team=teams["self_team"],
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


def main() -> None:
    with open(join("server", "config.py"), "w") as f:
        f.write(generate_config())
    process = Popen(["./start_server.sh"], cwd="server")
    signal(SIGTERM, lambda _, __: process.kill())
    exit(process.wait())


def healthcheck() -> None:
    config = load_config()
    actual = get(
        "http://127.0.0.1:5000", auth=("admin", config["farm"]["password"])
    ).text
    assert config["flag"]["format"] in actual
