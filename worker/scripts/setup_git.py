from __future__ import annotations
from worker.ssh import ssh_connect
from worker.config import CONFIG
from os.path import basename
from termcolor import cprint


def setup_git(*services: str, ip: str | None, port: int | None):
    """upload vulnbox's services on git

    - services: the folders of the services to upload on git
    - ip: override the ip found in the config file
    - port: override the port found in the config file"""
    with ssh_connect(ip, port, print_commands=True) as ssh:
        ssh.check_call("git config --global user.email adserver@example.com")
        ssh.check_call("git config --global user.name ADServer")
        for service in services:
            service_name = basename(service)
            if ssh.exists(f"{service}/.git"):
                cprint(
                    f"Warning: Skipping service {service} since the .git folder already exists",
                    "yellow",
                )
                continue
            ssh.check_call(f"git -C {service} init")
            ssh.check_call(f"git -C {service} add .")
            ssh.check_call(f"git -C {service} commit -m first")
            ssh.check_call(f"git -C {service} branch -M {service_name}")
            ssh.check_call(
                f"git -C {service} remote add origin {CONFIG['git']['git_repo']}"
            )
            ssh.check_call(f"git -C {service} push -u origin {service_name}")
