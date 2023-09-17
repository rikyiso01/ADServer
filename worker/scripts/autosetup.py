from subprocess import check_call, CalledProcessError
from typing import Annotated, Optional

from typer import Option
from worker.scripts.setup_keys import setup_keys
from worker.scripts.setup_git import setup_git
from termcolor import cprint


def autosetup(
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
    skip_git: Annotated[bool, Option(help="Skip git folders preparation")] = False,
    interface_ip: Annotated[
        Optional[str],
        Option(help="Override the vulnbox ip used to find the interface name"),
    ] = None,
    ssh_port: Annotated[
        Optional[int],
        Option(help="Change the vulnbox port used to skip ssh traffic with tcpdump"),
    ] = None,
):
    """Utility to run all the setup scripts"""
    print("Welcome, I am the auto-setupper, I will now setup some things for you")
    print("Now, I will install your team members key on the server")
    setup_keys(
        ip,
        port,
        skip_tools_install=skip_tools_install,
        skip_keys=skip_keys,
        skip_aliases=skip_aliases,
        skip_private_key=skip_private_key,
        skip_tcpdump=skip_tcpdump,
        interface_ip=interface_ip,
        ssh_port=ssh_port,
    )
    print("Done")
    _ = input(
        "Change the number of teams in the config.toml file then press enter to continue "
    )
    print("I will now start the support server")
    print("$ docker compose up -d")
    try:
        _ = check_call(["docker", "compose", "up", "-d"])
    except (CalledProcessError, OSError):
        cprint("Error running 'docker compose up -d'", "red")
        _ = input(
            "Please modify the above command and run it, the press enter to continue"
        )
    print("Done")
    if not skip_git:
        services: list[str] = []
        while not services:
            services = input("Write all services' name separated by a space: ").split()
        print("I will now setup the git repo")
        setup_git(services, ip=ip, port=port)
        print("Done")
    print("Have a good day, sir :)")
