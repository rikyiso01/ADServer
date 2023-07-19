from __future__ import annotations
from worker.ssh import ssh_connect, SSH
from worker.config import CONFIG, get_git_host, get_ssh_keys, escape_shell
from os.path import expanduser, expandvars
from typing import Literal
from typing_extensions import TypeAlias
from logging import getLogger

PackageManagers: TypeAlias = 'Literal["apt-get"]'
PACKAGE_MANAGERS: list[PackageManagers] = ["apt-get"]
PACKAGES: dict[str, dict[PackageManagers, str]] = {
    "tcpdump": {"apt-get": "tcpdump"},
    "ip": {"apt-get": "iproute2"},
    "git": {"apt-get": "git"},
}


def get_aliases(aliases: dict[str, str]) -> list[str]:
    for key in aliases:
        assert " " not in key
        assert "$" not in key
        assert "'" not in key
        assert '"' not in key
        assert "\\" not in key
        assert "(" not in key
        assert ")" not in key
    return [f'alias {key}="{escape_shell(value)}"' for key, value in aliases.items()]


def get_aliases_command(aliases: list[str]) -> str:
    return " && ".join(f'echo "{escape_shell(alias)}"' for alias in aliases)


def install_tools(ssh: SSH):
    while True:
        if ssh.run(f"command -v {' '.join(PACKAGES)}") == 0:
            break
        for package_manager in PACKAGE_MANAGERS:
            if ssh.run(f"command -v {package_manager}") == 0:
                ssh.check_call("apt-get update")
                packages = [
                    package_managers[package_manager]
                    for package_managers in PACKAGES.values()
                ]
                ssh.check_call(
                    f"apt-get install -y --no-install-recommends {' '.join(packages)}"
                )
            else:
                input(
                    f"No known package manager found on the server, please install {' '.join(PACKAGES)}, then press enter to continue"
                )


def install_keys(ssh: SSH):
    ssh.run("mkdir -p /root/.ssh")
    for key in get_ssh_keys(CONFIG["sshkeys"]["github_users"]):
        ssh.check_call(f"echo '{key}' >> /root/.ssh/authorized_keys")
    ssh.check_call(
        f"ssh-keyscan -t rsa {get_git_host(CONFIG['git']['git_repo'])} >> /root/.ssh/known_hosts"
    )


def install_aliases(ssh: SSH):
    ssh.check_call(
        f'({get_aliases_command(get_aliases(CONFIG["aliases"]))}) >> .profile',
    )


def install_private_key(ssh: SSH):
    ssh.put(
        expanduser(expandvars(CONFIG["git"]["ssh_key"])),
        "/root/.ssh/id_rsa",
    )
    ssh.check_call("chmod 600 /root/.ssh/id_rsa")


def start_tcpdump(ssh: SSH):
    ssh.check_call(f"mkdir -p {CONFIG['tcpdumper']['dumps_folder']}")
    ssh.run("pkill tcpdump")
    ssh.popen(
        f"tcpdump -w '{CONFIG['tcpdumper']['dumps_folder']}/%H-%M-%S.pcap' -G {CONFIG['tcpdumper']['interval']} -Z root -i '{CONFIG['tcpdumper']['interface']}' -z gzip not port {CONFIG['server']['port']} > /dev/null 2> /dev/null",
    )


def setup_keys(
    ip: str | None,
    port: int | None,
    /,
    *,
    skip_tools_install: bool = False,
    skip_keys: bool = False,
    skip_aliases: bool = False,
    skip_private_key: bool = False,
    skip_tcpdump: bool = False,
):
    logger = getLogger("setup_keys")
    logger.debug("Connecting to vulnbox")
    with ssh_connect(ip, port, print_commands=True) as ssh:
        if not skip_tools_install:
            logger.debug("Installing tools")
            install_tools(ssh)
        else:
            logger.debug("Skipping install tools")
        if not skip_keys:
            logger.debug("Installing keys")
            install_keys(ssh)
        else:
            logger.debug("Skipping install keys")
        if not skip_aliases:
            logger.debug("Installing aliases")
            install_aliases(ssh)
        else:
            logger.debug("Skipping install aliases")
        if not skip_private_key:
            logger.debug("Installing private key")
            install_private_key(ssh)
        else:
            logger.debug("Skipping install private key")
        if not skip_tcpdump:
            logger.debug("Starting tcpdump")
            start_tcpdump(ssh)
        else:
            logger.debug("Skipping start tcpdump")
