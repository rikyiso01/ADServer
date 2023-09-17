from __future__ import annotations
from collections.abc import Generator
from httpx import HTTPStatusError, RequestError, post, TransportError, get
from result import Err, Ok, Result
from worker.config import wait_for_host_ip, NETWORK_ATTEMPTS_INTERVAL, get_config
from subprocess import Popen
from time import sleep
from os import environ
from sys import exit
from logging import getLogger
from contextlib import contextmanager
from attrs import frozen

from worker.utils import add_sigterm

LOGGER = getLogger(__name__)


def caronte_check() -> None:
    LOGGER.debug("Healthchecking rules")
    config = get_config()
    auth = (config.caronte.username, config.caronte.password)
    response = get("http://127.0.0.1:3333/api/rules", auth=auth)
    if response.status_code != 200:
        LOGGER.warning(
            f"Healthchecking rules failed: status_code={response.status_code} text={response.text}"
        )
    assert response.status_code == 200, response.text
    LOGGER.debug("Halthchecking pcap sessions")
    response = get("http://127.0.0.1:3333/api/pcap/sessions", auth=auth)
    if response.status_code != 200:
        LOGGER.warning(
            f"Healthchecking pcap sessions failed: status_code={response.status_code} text={response.text}"
        )
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    result: list[object]
    if not result:
        LOGGER.warning(
            f"Healthchecking pcap sessions content failed: text={response.text}"
        )
    assert len(result) > 0


@frozen
class Caronte:
    _process: Popen[bytes]

    def setup(
        self,
        server_address: str,
        flag_regex: str,
        auth_required: bool,
        accounts: dict[str, str],
    ) -> Result[None, RequestError | HTTPStatusError]:
        try:
            response = post(
                "http://127.0.0.1:3333/setup",
                json={
                    "config": {
                        "server_address": server_address,
                        "flag_regex": flag_regex,
                        "auth_required": auth_required,
                    },
                    "accounts": accounts,
                },
            )
        except RequestError as e:
            return Err(e)
        if response.status_code != 202:
            LOGGER.warning(
                f"Caronte setup responded with non 202 http code: {response.status_code} {response.text}"
            )
            return Err(
                HTTPStatusError(
                    str(response.status_code),
                    request=response.request,
                    response=response,
                )
            )
        return Ok(None)


@contextmanager
def start_caronte() -> Generator[Result[Caronte, OSError], None, None]:
    try:
        process = Popen(
            [
                "./caronte",
                "-mongo-host",
                environ["MONGO_HOST"],
                "-assembly_memuse_log",
            ]
        )
    except OSError as e:
        yield Err(e)
        return
    try:
        yield Ok(Caronte(process))
    finally:
        process.kill()


def caronte() -> None:
    LOGGER.debug("Registering SIGTERM signal")
    add_sigterm()
    config = get_config()
    process = Popen(
        [
            "./caronte",
            "-mongo-host",
            environ["MONGO_HOST"],
            "-assembly_memuse_log",
        ]
    )
    while True:
        LOGGER.info("Trying to setup Caronte")
        host = config.server.host
        LOGGER.debug(f"Resolving vulnbox ip: {host}")
        resolved_ip = wait_for_host_ip(host)
        LOGGER.debug(f"Resolved vulnbox ip: {resolved_ip}")
        auth_required = len(config.caronte.username) != 0
        accounts = {config.caronte.username: config.caronte.password}
        try:
            response = post(
                "http://127.0.0.1:3333/setup",
                json={
                    "config": {
                        "server_address": resolved_ip,
                        "flag_regex": config.flag.format,
                        "auth_required": auth_required,
                    },
                    "accounts": accounts,
                },
            )
        except TransportError as e:
            LOGGER.error(
                f"Error setting up caronte, retrying in {NETWORK_ATTEMPTS_INTERVAL} seconds: {e}",
            )
            sleep(NETWORK_ATTEMPTS_INTERVAL)
            continue
        if response.status_code != 202:
            LOGGER.warning(
                f"Caronte setup responded with non 202 http code: {response.status_code} {response.text}"
            )
        LOGGER.debug(
            f"Caronte setup responded with status_code: {response.status_code} body: {response.text}"
        )
        break
    LOGGER.info("Caronte Setup completed, waiting for Caronte to exit")
    result_code = process.wait()
    if result_code != 0:
        LOGGER.fatal(f"Caronte exited with non 0 exit code: {result_code}")
    else:
        LOGGER.info("Caronte exited successfully")
    exit(result_code)
