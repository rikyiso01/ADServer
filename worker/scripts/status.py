from __future__ import annotations
from subprocess import run, PIPE, DEVNULL
from termcolor import cprint

SERVICES = ["destructivefarm", "caronte", "worker"]


def status():
    """Check if the services are working normally"""
    ok = True
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
            ok = False
            cprint("down", "dark_grey")
        elif healthy:
            cprint("ok", "light_green")
        else:
            ok = False
            cprint("error", "light_red")
    if not ok:
        exit(1)
