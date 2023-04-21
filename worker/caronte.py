from __future__ import annotations
from httpx import post, ConnectError, get
from worker.config import load_config
from subprocess import Popen
from time import sleep
from signal import signal, SIGTERM
from os import environ
from sys import exit, stderr
from socket import gethostbyname, gaierror


def healthcheck() -> None:
    response = get("http://127.0.0.1:3333/api/rules")
    assert response.status_code == 200, response.text


def main():
    process = Popen(
        [
            "./caronte",
            "-mongo-host",
            environ["MONGO_HOST"],
            "-mongo-port",
            environ["MONGO_PORT"],
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
                        "server_address": gethostbyname(config["server"]["host"]),
                        "flag_regex": config["flag"]["format"],
                        "auth_required": False,
                    },
                    "accounts": {},
                },
            )
            print(response.status_code, response.text, flush=True)
            break
        except gaierror as e:
            print(e, file=stderr, flush=True)
        except ConnectError as e:
            print(e, file=stderr, flush=True)
        sleep(1)
    exit(process.wait())
