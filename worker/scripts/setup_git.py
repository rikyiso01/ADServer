from shlex import quote
from typing import Annotated, Optional

from typer import Option
from worker.config import get_config
from worker.ssh import ssh_connect
from os.path import basename
from termcolor import cprint


def setup_git(
    services: Annotated[
        list[str], Option(help="The folders of the services to upload on git")
    ],
    ip: Annotated[
        Optional[str], Option(help="Override the ip found in the config file")
    ] = None,
    port: Annotated[
        Optional[int], Option(help="Override the port found in the config file")
    ] = None,
):
    """Upload vulnbox's services on git"""
    config = get_config()
    with ssh_connect(ip, port, print_commands=True) as result:
        ssh = result.unwrap()
        ssh.check_call("git config --global user.email adserver@example.com").unwrap()
        ssh.check_call("git config --global user.name ADServer").unwrap()
        for service in services:
            service_name = basename(service)
            if ssh.exists(f"{service}/.git").unwrap():
                cprint(
                    f"Warning: Skipping service {service} since the .git folder already exists",
                    "yellow",
                )
                continue
            ssh.check_call(f"git -C {quote(service)} init").unwrap()
            ssh.check_call(f"git -C {quote(service)} add .").unwrap()
            ssh.check_call(f"git -C {quote(service)} commit -m first").unwrap()
            ssh.check_call(
                f"git -C {quote(service)} branch -M {quote(service_name)}"
            ).unwrap()
            ssh.check_call(
                f"git -C {quote(service)} remote add origin {quote(config.git.git_repo)}"
            ).unwrap()
            ssh.check_call(
                f"git -C {quote(service)} push -u origin {quote(service_name)}"
            ).unwrap()
