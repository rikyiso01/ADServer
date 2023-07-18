from __future__ import annotations
from httpx import post, ConnectError, get
from worker.config import load_config, get_host_ip
from subprocess import Popen
from time import sleep
from signal import signal, SIGTERM
from os import environ
from sys import exit, stderr


def healthcheck() -> None:
    response = get("http://127.0.0.1:3333/api/rules")
    assert response.status_code == 200, response.text
    response = get("http://127.0.0.1:3333/api/pcap/sessions")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    result: list[object]
    assert len(result) > 0


def main():
    process = Popen(
        [
            "./caronte",
            "-mongo-host",
            environ["MONGO_HOST"],
            "-assembly_memuse_log",
        ]
    )

    def sigterm() -> None:
        print("SIGTERM", flush=True)
        process.kill()
        exit()

    signal(SIGTERM, lambda _, __: sigterm())
    config = load_config()
    while True:
        try:
            response = post(
                "http://127.0.0.1:3333/setup",
                json={
                    "config": {
                        "server_address": get_host_ip(config["server"]["host"]),
                        "flag_regex": config["flag"]["format"],
                        "auth_required": False,
                    },
                    "accounts": {},
                },
            )
            print(response.status_code, response.text, flush=True)
            break
        except ConnectError as e:
            print(e, file=stderr, flush=True)
        sleep(1)
    exit(process.wait())
