from __future__ import annotations
from subprocess import check_call, CalledProcessError
from worker.scripts.setup_keys import setup_keys
from worker.scripts.setup_git import setup_git
from termcolor import cprint


def autosetup(
    ip: str | None,
    port: int | None,
    /,
    *,
    skip_tools_install: bool,
    skip_keys: bool,
    skip_aliases: bool,
    skip_private_key: bool,
    skip_tcpdump: bool,
    skip_git: bool,
    interface_ip: str | None,
    ssh_port: int | None,
):
    """utility to run all the setup scripts

    - ip: override the ip found in the config file
    - port: override the port found in the config file
    - skip_tools_install: skip the vulnbox's tools checking and installation
    - skip_keys: skip team's members' keys installation
    - skip_aliases: skip aliases installation
    - skip_private_key: skip private key installation
    - skip_tcpdump: skip tcpdump start
    - skip_git: skip git folders preparation
    - interface_ip: override the vulnbox ip used to find the interface name
    - ssh_port: change the vulnbox port used to skip ssh traffic with tcpdump"""
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
    input(
        "Change the number of teams in the config.toml file then press enter to continue "
    )
    print("I will now start the support server")
    print("$ docker compose up -d")
    try:
        check_call(["docker", "compose", "up", "-d"])
    except CalledProcessError:
        cprint("Error running 'docker compose up -d'", "red")
        input("Please modify the above command and run it, the press enter to continue")
    print("Done")
    if not skip_git:
        services: list[str] = []
        while not services:
            services = input("Write all services' name separated by a space: ").split()
        print("I will now setup the git repo")
        setup_git(*services, ip=ip, port=port)
        print("Done")
    print("Have a good day, sir :)")
