from __future__ import annotations
from subprocess import run, PIPE, DEVNULL

SERVICES = ["destructivefarm", "caronte", "worker"]


def status():
    for service in SERVICES:
        print(
            f"$ docker inspect --format='{{{{json .State.Health.Status}}}}' adserver-{service}"
        )
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
