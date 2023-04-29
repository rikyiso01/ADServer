from __future__ import annotations
from worker.caronte import main as caronte, healthcheck as caronte_check
from argparse import ArgumentParser
from worker.destructivefarm import (
    main as destructivefarm,
    healthcheck as destructivefarm_check,
)
from worker.rsyncer import main as worker, healthcheck as worker_check
from worker.scripts import setup_git, setup_keys, autosetup, status, check_keys


def main():
    parser = ArgumentParser()
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
    subparser = sub.add_parser("setup_git")
    subparser.add_argument("--ip", default=None)
    subparser.add_argument("--port", default=None, type=int)
    subparser.add_argument("services", nargs="+")
    subparser = sub.add_parser("autosetup")
    subparser.add_argument("ip", default=None, nargs="?")
    subparser.add_argument("port", default=None, nargs="?")
    subparser = sub.add_parser("status")
    subparser = sub.add_parser("check_keys")
    args = parser.parse_args()
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
            assert False
    elif args.script == "setup_keys":
        setup_keys(args.ip, args.port)
    elif args.script == "setup_git":
        setup_git(args.services, args.ip, args.port)
    elif args.script == "autosetup":
        autosetup(args.ip, args.port)
    elif args.script == "status":
        status()
    elif args.script == "check_keys":
        check_keys()
    else:
        assert False, "Option not implemented"


if __name__ == "__main__":
    main()
