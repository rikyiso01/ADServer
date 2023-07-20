from __future__ import annotations
from httpx import post, TransportError, get
from worker.config import get_host_ip, NETWORK_ATTEMPTS_INTERVAL, CONFIG
from subprocess import Popen
from time import sleep
from signal import signal, SIGTERM
from os import environ
from sys import exit
from logging import getLogger


def healthcheck() -> None:
    logger = getLogger("caronte.healthcheck")
    logger.debug("Healthchecking rules")
    response = get(
        "http://127.0.0.1:3333/api/rules",
        auth=(CONFIG["caronte"]["username"], CONFIG["caronte"]["password"]),
    )
    if response.status_code != 200:
        logger.warning(
            f"Healthchecking rules failed: status_code={response.status_code} text={response.text}"
        )
    assert response.status_code == 200, response.text
    logger.debug("Halthchecking pcap sessions")
    response = get(
        "http://127.0.0.1:3333/api/pcap/sessions",
        auth=(CONFIG["caronte"]["username"], CONFIG["caronte"]["password"]),
    )
    if response.status_code != 200:
        logger.warning(
            f"Healthchecking pcap sessions failed: status_code={response.status_code} text={response.text}"
        )
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    result: list[object]
    if not result:
        logger.warning(
            f"Healthchecking pcap sessions content failed: text={response.text}"
        )
    assert len(result) > 0


def main():
    logger = getLogger("caronte")
    logger.info("Spawning caronte process")
    process = Popen(
        [
            "./caronte",
            "-mongo-host",
            environ["MONGO_HOST"],
            "-assembly_memuse_log",
        ]
    )

    def sigterm() -> None:
        logger.info("Received SIGTERM")
        process.kill()
        exit()

    logger.debug("Registering SIGTERM signal")
    signal(SIGTERM, lambda _, __: sigterm())
    while True:
        logger.info("Trying to setup Caronte")
        host = CONFIG["server"]["host"]
        logger.debug(f"Resolving vulnbox ip: {host}")
        resolved_ip = get_host_ip(host)
        logger.debug(f"Resolved vulnbox ip: {resolved_ip}")
        auth_required = len(CONFIG["caronte"]["username"]) != 0
        accounts = {CONFIG["caronte"]["username"]: CONFIG["caronte"]["password"]}
        try:
            response = post(
                "http://127.0.0.1:3333/setup",
                json={
                    "config": {
                        "server_address": resolved_ip,
                        "flag_regex": CONFIG["flag"]["format"],
                        "auth_required": auth_required,
                    },
                    "accounts": accounts,
                },
            )
        except TransportError as e:
            logger.error(
                f"Error setting up caronte, retrying in {NETWORK_ATTEMPTS_INTERVAL} seconds: {e}",
            )
            sleep(NETWORK_ATTEMPTS_INTERVAL)
            continue
        if response.status_code != 202:
            logger.warning(
                f"Caronte setup responded with non 202 http code: {response.status_code} {response.text}"
            )
        logger.debug(
            f"Caronte setup responded with status_code: {response.status_code} body: {response.text}"
        )
        break
    logger.info("Caronte Setup completed, waiting for Caronte to exit")
    result_code = process.wait()
    if result_code != 0:
        logger.fatal(f"Caronte exited with non 0 exit code: {result_code}")
    else:
        logger.info("Caronte exited successfully")
    exit(result_code)
