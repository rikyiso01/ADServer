from worker.ssh import SSH
from worker.caronte import healthcheck


def test_healthcheck(remote_server: SSH) -> None:
    healthcheck()
