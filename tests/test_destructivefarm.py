from __future__ import annotations
from worker.destructivefarm import generate_config, destructivefarm_check
from worker.config import Config
from typing import Any
from os.path import join
from worker.ssh import SSH


def exec_config_py(code: str) -> dict[str, Any]:
    globals: dict[str, Any] = {}
    exec(code, globals)
    return globals["CONFIG"]


def test_destructivefarm_config_generation(test_config: Config) -> None:
    with open(join("destructivefarm", "src", "server", "config.py")) as f:
        expected = exec_config_py(f.read())
    actual = exec_config_py(generate_config("10.0.0.2"))
    assert "Team #2" not in actual["TEAMS"]
    actual["TEAMS"]["Team #2"] = "10.0.0.2"
    assert actual == expected


def test_destructivefarm_healthcheck(remote_server: SSH) -> None:
    destructivefarm_check()
