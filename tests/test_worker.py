from __future__ import annotations
from worker.worker import worker_check
from worker.ssh import SSH
from tempfile import TemporaryDirectory
from subprocess import check_call
from os.path import join


def test_worker_healthcheck(remote_server: SSH) -> None:
    with TemporaryDirectory() as tmp:
        _ = check_call(["docker", "compose", "cp", "worker:/data", tmp])
        tmp = join(tmp, "data")
        worker_check("127.0.0.1", 2222, tmp)
