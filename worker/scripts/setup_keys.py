from __future__ import annotations
from worker.ssh import ssh_connect, SSH
from worker.config import CONFIG, get_git_host, get_ssh_keys, escape_shell, get_host_ip
from os.path import expanduser, expandvars
from typing import Literal
from typing_extensions import TypeAlias
from logging import getLogger
from termcolor import cprint

PackageManagers: TypeAlias = 'Literal["apt-get"]'
PACKAGE_MANAGERS: list[PackageManagers] = ["apt-get"]
PACKAGES: dict[str, dict[PackageManagers, str]] = {
    "tcpdump": {"apt-get": "tcpdump"},
    "ip": {"apt-get": "iproute2"},
    "git": {"apt-get": "git"},
}


def get_interface_name(ssh: SSH, interface_ip: str) -> str | None:
    interface_ip = get_host_ip(interface_ip)
    exit_code, stdout, stderr = ssh.run_output("ip -brief address show")
    print(stdout.decode())
    if stderr:
        cprint(stderr.decode(), "light_red")
        return None
    if exit_code != 0:
        cprint(f"Error: the command exited with non 0 exit code: {exit_code}")
        return None
    result: list[str] = []
    stdout = stdout.decode()
    for line in stdout.splitlines():
        if interface_ip in line:
            result.append(line.split()[0])
    if len(result) == 0:
        cprint(f"No interface found with the ip {interface_ip}")
        return None
    if len(result) > 1:
        cprint(f"Multiple interfaces found with the ip {interface_ip}: {result}")
        return None
    (interface_name,) = result
    return interface_name


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
    if ssh.run(f"command -v {' '.join(PACKAGES)}") != 0:
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
                break
        else:
            input(
                f"No known package manager found on the server, please install {' '.join(PACKAGES)} commands, then press enter to continue"
            )
        while ssh.run(f"command -v {' '.join(PACKAGES)}") != 0:
            input(
                f"Something went wrong while installing the packages, please install {' '.join(PACKAGES)} commands, then press enter to continue"
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


def start_tcpdump(ssh: SSH, interface_ip: str | None, ssh_port: int | None):
    if interface_ip is None:
        interface_ip = CONFIG["server"]["host"]
    if ssh_port is None:
        ssh_port = CONFIG["server"]["port"]
    interface = get_interface_name(ssh, interface_ip)
    if interface is None:
        interface = input(
            "Error getting the interface name, please find the interface to use with 'ip a' and write the name here: "
        )
    if "@" in interface:
        interface, _ = interface.split("@")
    print("The interface name is", interface)
    ssh.check_call(f"mkdir -p {CONFIG['tcpdumper']['dumps_folder']}")
    ssh.run("pkill tcpdump")
    ssh.popen(
        f"tcpdump -w '{CONFIG['tcpdumper']['dumps_folder']}/%H-%M-%S.pcap' -G {CONFIG['tcpdumper']['interval']} -Z root -i '{interface}' -z gzip not port {ssh_port} > /dev/null 2> /dev/null",
    )


def setup_keys(
    ip: str | None,
    port: int | None,
    /,
    *,
    skip_tools_install: bool,
    skip_keys: bool,
    skip_aliases: bool,
    skip_private_key: bool,
    skip_tcpdump: bool,
    interface_ip: str | None,
    ssh_port: int | None,
):
    """prepare the vulnbox

    - ip: override the ip found in the config file
    - port: override the port found in the config file
    - skip_tools_install: skip the vulnbox's tools checking and installation
    - skip_keys: skip team's members' keys installation
    - skip_aliases: skip aliases installation
    - skip_private_key: skip private key installation
    - skip_tcpdump: skip tcpdump start
    - interface_ip: override the vulnbox ip used to find the interface name
    - ssh_port: change the vulnbox port used to skip ssh traffic with tcpdump"""
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
            start_tcpdump(ssh, interface_ip, ssh_port)
        else:
            logger.debug("Skipping start tcpdump")
