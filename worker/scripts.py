from __future__ import annotations
from worker.ssh import ssh_connect
from worker.config import (
    load_config,
    get_git_host,
    get_ssh_keys,
    escape_shell,
    get_ssh_key,
    SERVER_DUMPS_FOLDER,
)
from os.path import basename, join, expanduser, expandvars
from subprocess import check_call, run, PIPE, DEVNULL


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


def setup_keys(ip: str | None, port: int | None):
    config = load_config()
    with ssh_connect(ip, port) as ssh:
        while ssh.run("command -v tcpdump ip git") != 0:
            if ssh.run("command -v apt-get") == 0:
                ssh.check_call("apt-get update")
                ssh.check_call(
                    "apt-get install -y --no-install-recommends tcpdump iproute2 git"
                )
            else:
                input(
                    "No known package manager found on the server, please install tcpdump iproute2 git, then press enter to continue"
                )
        if not ssh.exists(join("/", "root", ".ssh")):
            ssh.sftp.mkdir(join("/", "root", ".ssh"))
        for key in get_ssh_keys(config["sshkeys"]["github_users"]):
            ssh.check_call(f"echo '{key}' >> /root/.ssh/authorized_keys")
        ssh.check_call(
            f"ssh-keyscan -t rsa {get_git_host(config['git']['git_repo'])} >> {join('/','root','.ssh','known_hosts')}"
        )
        ssh.check_call(
            f'({get_aliases_command(get_aliases(config["aliases"]))}) >> .profile'
        )
        ssh.sftp.put(
            expanduser(expandvars(config["git"]["ssh_key"])),
            join("/", "root", ".ssh", "id_rsa"),
        )
        ssh.check_call("chmod 600 /root/.ssh/id_rsa")
        ssh.run("pkill tcpdump")
        ssh.check_call("mkdir -p dumps")
        ssh.check_call("rm -f dumps/*.pcap")
        ssh.popen(
            f"tcpdump -w '{SERVER_DUMPS_FOLDER}/%H-%M-%S.pcap' -G {config['tcpdumper']['interval']} -Z root -i '{config['tcpdumper']['interface']}' -z gzip not port {config['server']['port']} > /dev/null 2> /dev/null",
        )


def setup_git(services: list[str], ip: str | None, port: int | None):
    config = load_config()
    with ssh_connect(ip, port) as ssh:
        ssh.check_call("git config --global user.email adserver@example.com")
        ssh.check_call("git config --global user.name ADServer")
        for service in services:
            service_name = basename(service)
            assert not ssh.exists(join(service, ".git")), "git folder already exists"
            ssh.check_call(f"git -C {service} init")
            ssh.check_call(f"git -C {service} add .")
            ssh.check_call(f"git -C {service} commit -m first")
            ssh.check_call(f"git -C {service} branch -M {service_name}")
            ssh.check_call(
                f"git -C {service} remote add origin {config['git']['git_repo']}"
            )
            ssh.check_call(f"git -C {service} push -u origin {service_name}")


def autosetup(ip: str | None, port: int | None):
    print("Welcome, I am the auto-setupper, I will now setup some things for you")
    print("Now, I will install your team members key on the server")
    setup_keys(ip, port)
    print("Done")
    print("You can now login to check the interface name with 'ip a'")
    input(
        "Change the interface name and the number of teams in the config.toml file then press enter to continue "
    )
    print("I will now start the support server")
    check_call(["docker", "compose", "up", "-d"])
    print("Done")
    services: list[str] = []
    while not services:
        services = input("Write all services' name separated by a space: ").split()
    print("I will now setup the git repo")
    setup_git(services, ip, port)
    print("Done")
    print("Have a good day, sir :)")


SERVICES = ["destructivefarm", "caronte", "worker"]


def status():
    for service in SERVICES:
        process = run(
            [
                "docker",
                "inspect",
                "--format='{{json .State.Health.Status}}'",
                f"adserver-{service}",
            ],
            text=True,
            stdout=PIPE,
            stderr=DEVNULL,
        )
        output = process.stdout
        up = process.returncode == 0
        healthy = output.strip().strip("'").strip('"') == "healthy"
        print(f"{service}: ", end="")
        if not up:
            print("\033[90mdown", end="")
        elif healthy:
            print("\033[92mok", end="")
        else:
            print("\033[91merror", end="")
        print("\x1b[0m")


def check_keys():
    config = load_config()
    for user in config["sshkeys"]["github_users"]:
        if not get_ssh_key(user):
            print(user, "has no ssh keys")
