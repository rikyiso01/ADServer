from worker.ssh import ssh_connect
from worker.config import load_config, get_git_host, get_ssh_keys, get_aliases
from os.path import basename, join, expanduser, expandvars
from subprocess import check_call, run, PIPE, DEVNULL


def setup_keys(ip: str | None, port: int | None):
    config = load_config()
    with ssh_connect(ip, port) as ssh:
        ssh.check_call("apt-get update")
        ssh.check_call(
            "apt-get install -y --no-install-recommends tcpdump iproute2 git"
        )
        if not ssh.exists(join("/", "root", ".ssh")):
            ssh.sftp.mkdir(join("/", "root", ".ssh"))
        for key in get_ssh_keys(config["sshkeys"]["github_users"]):
            ssh.check_call(f"echo '{key}' >> /root/.ssh/authorized_keys")
        ssh.check_call(
            f"ssh-keyscan -t rsa {get_git_host(config['git']['git_repo'])} >> {join('/','root','.ssh','known_hosts')}"
        )
        ssh.check_call(
            f'echo "{get_aliases(config["aliases"])}" >> {join("/","root",".profile")}'
        )
        ssh.sftp.put(
            expanduser(expandvars(config["git"]["ssh_key"])),
            join("/", "root", ".ssh", "id_rsa"),
        )
        ssh.check_call("chmod 600 /root/.ssh/id_rsa")


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
    setup_keys(ip, port)
    print("You can now login to check the interface name with 'ip a'")
    input("Change interface name in config.toml then press enter to continue ")
    check_call(["docker-compose", "up", "-d"])
    services: list[str] = []
    while not services:
        services = input("Write all services' name separated by a space: ").split()
    setup_git(services, ip, port)


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
