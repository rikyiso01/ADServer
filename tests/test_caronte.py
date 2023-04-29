from __future__ import annotations
from worker.ssh import SSH
from worker.caronte import healthcheck


def test_caronte_healthcheck(remote_server: SSH) -> None:
    healthcheck()
