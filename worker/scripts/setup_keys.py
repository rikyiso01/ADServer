from result import Err, Ok, Result
from typer import Option
from worker.ssh import SSHError, ssh_connect, SSH
from worker.config import (
    get_config,
    get_git_host,
    get_ssh_keys,
    wait_for_host_ip,
)
from os.path import expanduser, expandvars
from typing import Annotated, Literal, Optional
from typing_extensions import TypeAlias
from logging import getLogger
from termcolor import cprint
from shlex import quote
from traceback import print_exception

PackageManagers: TypeAlias = 'Literal["apt-get"]'
PACKAGE_MANAGERS: list[PackageManagers] = ["apt-get"]
PACKAGES: dict[str, dict[PackageManagers, str]] = {
    "tcpdump": {"apt-get": "tcpdump"},
    "ip": {"apt-get": "iproute2"},
    "git": {"apt-get": "git"},
}
LOGGER = getLogger(__name__)


def get_interface_name(ssh: SSH, interface_ip: str) -> Result[str, SSHError | None]:
    interface_ip = wait_for_host_ip(interface_ip)
    result = ssh.run("ip -brief address show")
    if isinstance(result, Err):
        return result
    exit_code, stdout, stderr = result.ok_value
    print(stdout.decode())
    if stderr:
        cprint(stderr.decode(), "light_red")
        return Err(None)
    if exit_code != 0:
        cprint(
            f"Error: the command exited with non 0 exit code: {exit_code}", "light_red"
        )
        return Err(None)
    interfaces: list[str] = []
    stdout = stdout.decode()
    for line in stdout.splitlines():
        if interface_ip in line:
            interfaces.append(line.split()[0])
    if len(interfaces) == 0:
        cprint(f"No interface found with the ip {interface_ip}", "light_red")
        return Err(None)
    if len(interfaces) > 1:
        cprint(
            f"Multiple interfaces found with the ip {interface_ip}: {result}",
            "light_red",
        )
        return Err(None)
    (interface_name,) = interfaces
    return Ok(interface_name)


def get_aliases(aliases: dict[str, str]) -> list[str]:
    for key in aliases:
        assert "=" not in key
    return [f"alias {quote(key)}={quote(value)}" for key, value in aliases.items()]


def get_aliases_command(aliases: list[str]) -> str:
    return " && ".join(f"echo {quote(alias)}" for alias in aliases)


def install_tools(ssh: SSH):
    all_packages = " ".join(quote(package) for package in PACKAGES)
    if ssh.call(f"command -v {all_packages}").unwrap() != 0:
        ok = False
        for package_manager in PACKAGE_MANAGERS:
            if ssh.call(f"command -v {quote(package_manager)}").unwrap() == 0:
                ssh.check_call("apt-get update").unwrap()
                packages = [
                    package_managers[package_manager]
                    for package_managers in PACKAGES.values()
                ]
                ssh.check_call(
                    f"apt-get install -y --no-install-recommends {' '.join(quote(package) for package in packages)}"
                ).unwrap()
                ok = True
                break
        if not ok:
            _ = input(
                f"No known package manager found on the server, please install {' '.join(PACKAGES)!r} commands, then press enter to continue"
            )
        while ssh.call(f"command -v {all_packages}").unwrap() != 0:
            _ = input(
                f"Something went wrong while installing the packages, please install {' '.join(PACKAGES)!r} commands, then press enter to continue"
            )


def install_keys(ssh: SSH):
    config = get_config()
    _ = ssh.call("mkdir -p /root/.ssh").unwrap()
    for key in get_ssh_keys(config.sshkeys.github_users).unwrap():
        ssh.check_call(f"echo {quote(key)} >> /root/.ssh/authorized_keys").unwrap()
    ssh.check_call(
        f"ssh-keyscan -t rsa {quote(get_git_host(config.git.git_repo).unwrap())} >> /root/.ssh/known_hosts"
    ).unwrap()


def install_aliases(ssh: SSH):
    config = get_config()
    ssh.check_call(
        f"({get_aliases_command(get_aliases(config.aliases))}) >> .profile",
    ).unwrap()


def install_private_key(ssh: SSH):
    config = get_config()
    ssh.put(
        expanduser(expandvars(config.git.ssh_key)),
        "/root/.ssh/id_rsa",
    ).unwrap()
    ssh.check_call("chmod 600 /root/.ssh/id_rsa").unwrap()


def start_tcpdump(ssh: SSH, interface_ip: str | None, ssh_port: int | None):
    config = get_config()
    if interface_ip is None:
        interface_ip = config.server.host
    if ssh_port is None:
        ssh_port = config.server.port
    match get_interface_name(ssh, interface_ip):
        case Ok(value):
            interface = value
        case Err(e):
            print_exception(e)
            interface = input(
                "Error getting the interface name, please find the interface to use with 'ip a' and write the name here: "
            )
    if "@" in interface:
        interface, _ = interface.split("@")
    print("The interface name is", interface)
    ssh.check_call(f"mkdir -p {quote(config.tcpdumper.dumps_folder)}").unwrap()
    _ = ssh.call("pkill tcpdump").unwrap()
    ssh.popen(
        f"tcpdump -w {quote(config.tcpdumper.dumps_folder)}/%H-%M-%S.pcap -G {config.tcpdumper.interval} -Z root -i {quote(interface)} -z gzip not port {ssh_port} > /dev/null 2> /dev/null",
    ).unwrap()


def setup_keys(
    ip: Annotated[
        Optional[str], Option(help="Override the ip found in the config file")
    ] = None,
    port: Annotated[
        Optional[int], Option(help="Override the port found in the config file")
    ] = None,
    skip_tools_install: Annotated[
        bool, Option(help="Skip the vulnbox's tools checking and installation")
    ] = False,
    skip_keys: Annotated[
        bool, Option(help="Skip team's members' keys installation")
    ] = False,
    skip_aliases: Annotated[bool, Option(help="Skip aliases installation")] = False,
    skip_private_key: Annotated[
        bool, Option(help="Skip private key installation")
    ] = False,
    skip_tcpdump: Annotated[bool, Option(help="Skip tcpdump start")] = False,
    interface_ip: Annotated[
        Optional[str],
        Option(help="Override the vulnbox ip used to find the interface name"),
    ] = None,
    ssh_port: Annotated[
        Optional[int],
        Option(help="Change the vulnbox port used to skip ssh traffic with tcpdump"),
    ] = None,
):
    """Prepare the vulnbox"""
    LOGGER.debug("Connecting to vulnbox")
    with ssh_connect(ip, port, print_commands=True) as ssh:
        ssh = ssh.unwrap()
        if not skip_tools_install:
            LOGGER.debug("Installing tools")
            install_tools(ssh)
        else:
            LOGGER.debug("Skipping install tools")
        if not skip_keys:
            LOGGER.debug("Installing keys")
            install_keys(ssh)
        else:
            LOGGER.debug("Skipping install keys")
        if not skip_aliases:
            LOGGER.debug("Installing aliases")
            install_aliases(ssh)
        else:
            LOGGER.debug("Skipping install aliases")
        if not skip_private_key:
            LOGGER.debug("Installing private key")
            install_private_key(ssh)
        else:
            LOGGER.debug("Skipping install private key")
        if not skip_tcpdump:
            LOGGER.debug("Starting tcpdump")
            start_tcpdump(ssh, interface_ip, ssh_port)
        else:
            LOGGER.debug("Skipping start tcpdump")
