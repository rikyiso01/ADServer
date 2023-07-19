from __future__ import annotations
from subprocess import check_call, CalledProcessError
from worker.scripts.setup_keys import setup_keys
from worker.scripts.setup_git import setup_git


def autosetup(
    ip: str | None,
    port: int | None,
    skip_tools_install: bool,
    skip_keys: bool,
    skip_aliases: bool,
    skip_private_key: bool,
    skip_tcpdump: bool,
    skip_git: bool,
):
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
    )
    print("Done")
    print("You can now login to check the interface name with 'ip a'")
    input(
        "Change the interface name and the number of teams in the config.toml file then press enter to continue "
    )
    print("I will now start the support server")
    print("$ docker compose up -d")
    try:
        check_call(["docker", "compose", "up", "-d"])
    except CalledProcessError:
        print("Error running 'docker compose up -d'")
        input("Please modify the above command and run it, the press enter to continue")
    print("Done")
    if not skip_git:
        services: list[str] = []
        while not services:
            services = input("Write all services' name separated by a space: ").split()
        print("I will now setup the git repo")
        setup_git(services, ip, port)
        print("Done")
    print("Have a good day, sir :)")
