from __future__ import annotations
from worker.ssh import ssh_connect
from worker.config import CONFIG
from os.path import basename


def setup_git(services: list[str], ip: str | None, port: int | None):
    with ssh_connect(ip, port, print_commands=True) as ssh:
        ssh.check_call("git config --global user.email adserver@example.com")
        ssh.check_call("git config --global user.name ADServer")
        for service in services:
            service_name = basename(service)
            if ssh.exists(f"{service}/.git"):
                print(
                    f"\033[93mWarning: Skipping service {service} since the .git folder already exists\033[0m"
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
