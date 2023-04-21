from worker.rsyncer import healthcheck
from worker.ssh import SSH
from httpx import get
from worker.config import SERVER_DUMPS_FOLDER
from os import listdir
from os.path import join, splitext
from tempfile import TemporaryDirectory
from subprocess import check_call


def test_healthcheck(remote_server: SSH) -> None:
    healthcheck("127.0.0.1", 2222)


def test_upload(remote_server: SSH) -> None:
    response = get("http://127.0.0.1:3333/api/pcap/sessions")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    result: list[object]
    assert len(result) > 0


def test_local_folder(remote_server: SSH) -> None:
    with TemporaryDirectory() as tmp:
        check_call(["docker-compose", "cp", "worker:/data", tmp])
        tmp = join(tmp, "data")
        assert len(listdir(join(tmp, "compressed"))) <= 1
        assert len(listdir(join(tmp, "uncompressed"))) <= 1
        assert len(listdir(join(tmp, "backup"))) >= 3
        for name in listdir(join(tmp, "compressed")):
            assert splitext(name)[1] == ".gz"
        for name in listdir(join(tmp, "uncompressed")):
            assert splitext(name)[1] == ".pcap"
        for name in listdir(join(tmp, "backup")):
            assert splitext(name)[1] == ".pcap"


def test_remote_folder(remote_server: SSH) -> None:
    assert len(remote_server.sftp.listdir(SERVER_DUMPS_FOLDER)) <= 2
