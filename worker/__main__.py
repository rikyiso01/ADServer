from __future__ import annotations
from worker.caronte import main as caronte, healthcheck as caronte_check
from argparse import ArgumentParser
from worker.destructivefarm import (
    main as destructivefarm,
    healthcheck as destructivefarm_check,
)
from worker.rsyncer import main as worker, healthcheck as worker_check
from worker.scripts.setup_git import setup_git
from worker.scripts.setup_keys import setup_keys
from worker.scripts.autosetup import autosetup
from worker.scripts.status import status
from worker.scripts.check_keys import check_keys
from worker.config import load_config
from logging import basicConfig, INFO, DEBUG
from os import environ
from pydantic import ValidationError
from sys import stderr


def main():
    basicConfig(level=DEBUG if "DEBUG" in environ and environ["DEBUG"] else INFO)
    parser = ArgumentParser(prog="poetry run python -m worker")
    parser.add_argument("-c", "--config-file", default="config.toml")
    sub = parser.add_subparsers(required=True, dest="script")
    subparser = sub.add_parser("server")
    subparser.add_argument(
        "service",
        choices=[
            "caronte",
            "destructivefarm",
            "destructivefarm_check",
            "caronte_check",
            "worker",
            "worker_check",
        ],
    )
    subparser = sub.add_parser("setup_keys")
    subparser.add_argument("ip", default=None, nargs="?")
    subparser.add_argument("port", default=None, nargs="?")
    subparser.add_argument("--skip-tools-install", action="store_true", default=False)
    subparser.add_argument("--skip-keys", action="store_true", default=False)
    subparser.add_argument("--skip-aliases", action="store_true", default=False)
    subparser.add_argument("--skip-private-key", action="store_true", default=False)
    subparser.add_argument("--skip-tcpdump", action="store_true", default=False)
    subparser = sub.add_parser("setup_git")
    subparser.add_argument("--ip", default=None)
    subparser.add_argument("--port", default=None, type=int)
    subparser.add_argument("services", nargs="+")
    subparser = sub.add_parser("autosetup")
    subparser.add_argument("ip", default=None, nargs="?")
    subparser.add_argument("port", default=None, nargs="?")
    subparser.add_argument("--skip-tools-install", action="store_true", default=False)
    subparser.add_argument("--skip-keys", action="store_true", default=False)
    subparser.add_argument("--skip-aliases", action="store_true", default=False)
    subparser.add_argument("--skip-private-key", action="store_true", default=False)
    subparser.add_argument("--skip-tcpdump", action="store_true", default=False)
    subparser.add_argument("--skip-git", action="store_true", default=False)
    subparser = sub.add_parser("status")
    subparser = sub.add_parser("check_keys")
    args = parser.parse_args()
    try:
        load_config(args.config_file)
    except ValidationError as e:
        print(f"\033[91mError validating {args.config_file}", file=stderr)
        errors = e.errors(include_url=False)
        for error in errors:
            print(
                error["msg"] + ":", ".".join(str(c) for c in error["loc"]), file=stderr
            )
        print("\x1b[0m", end="")
        exit(1)
    if args.script == "server":
        if args.service == "caronte":
            caronte()
        elif args.service == "caronte_check":
            caronte_check()
        elif args.service == "destructivefarm":
            destructivefarm()
        elif args.service == "destructivefarm_check":
            destructivefarm_check()
        elif args.service == "worker":
            worker()
        elif args.service == "worker_check":
            worker_check()
        else:
            assert False, "Server option not implemented"
    elif args.script == "setup_keys":
        setup_keys(
            args.ip,
            args.port,
            skip_tools_install=args.skip_tools_install,
            skip_keys=args.skip_keys,
            skip_aliases=args.skip_aliases,
            skip_private_key=args.skip_private_key,
            skip_tcpdump=args.skip_tcpdump,
        )
    elif args.script == "setup_git":
        setup_git(args.services, args.ip, args.port)
    elif args.script == "autosetup":
        autosetup(
            args.ip,
            args.port,
            skip_tools_install=args.skip_tools_install,
            skip_keys=args.skip_keys,
            skip_aliases=args.skip_aliases,
            skip_private_key=args.skip_private_key,
            skip_tcpdump=args.skip_tcpdump,
            skip_git=args.skip_git,
        )
    elif args.script == "status":
        status()
    elif args.script == "check_keys":
        check_keys()
    else:
        assert False, "Option not implemented"


if __name__ == "__main__":
    main()
