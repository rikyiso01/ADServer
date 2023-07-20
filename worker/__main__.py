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
from worker.scripts.check_repo import check_repo
from worker.config import load_config
from logging import basicConfig, INFO, DEBUG
from pydantic import ValidationError
from termcolor import cprint
from inspect import signature, Parameter
from typing import Any

SCRIPTS = [setup_git, setup_keys, autosetup, status, check_keys, check_repo]
SERVER_COMMANDS = {
    "caronte": caronte,
    "caronte_check": caronte_check,
    "destructivefarm": destructivefarm,
    "destructivefarm_check": destructivefarm_check,
    "worker": worker,
    "worker_check": worker_check,
}


def parse_docstring(docstring: str) -> tuple[str, dict[str, str]]:
    lines = [l.strip() for l in docstring.splitlines()]
    if "" not in lines:
        return " ".join(lines), {}
    index = lines.index("")
    description = " ".join(lines[:index])
    args = lines[index + 1 :]
    result: dict[str, str] = {}
    for arg in args:
        assert arg.startswith("- ")
        index = arg.index(": ")
        key = arg[2:index]
        value = arg[index + 2 :]
        result[key] = value
    return description, result


def main():
    parser = ArgumentParser(prog="poetry run python -m worker")
    parser.add_argument(
        "-c",
        "--config-file",
        default="config.toml",
        help="change the config file location",
    )
    parser.add_argument(
        "-d", "--debug", default=False, action="store_true", help="add more logs"
    )
    sub = parser.add_subparsers(required=True, dest="script")
    subparser = sub.add_parser("server", help="commands used by the docker images")
    subparser.add_argument("service", choices=[command for command in SERVER_COMMANDS])
    for script in SCRIPTS:
        assert script.__doc__ is not None
        description, args_help = parse_docstring(script.__doc__)
        subparser = sub.add_parser(script.__name__, help=description)
        sign = signature(script)
        for parameter in sign.parameters.values():
            assert (
                parameter.name in args_help
            ), f"{parameter.name} {args_help} {description}"
            help = args_help[parameter.name]
            assert (
                parameter.annotation == "bool"
                or "None" in parameter.annotation
                or parameter.kind == Parameter.VAR_POSITIONAL
            ), f"{script.__name__}({parameter.name}: {parameter.annotation})"
            if parameter.kind == Parameter.KEYWORD_ONLY:
                subparser.add_argument(
                    f"--{parameter.name.replace('_','-')}",
                    action="store_true" if parameter.annotation == "bool" else "store",
                    default=False if parameter.annotation == "bool" else None,
                    help=help,
                )
            elif parameter.kind == Parameter.VAR_POSITIONAL:
                subparser.add_argument(parameter.name, nargs="+", help=help)
            elif parameter.kind == Parameter.POSITIONAL_ONLY:
                subparser.add_argument(parameter.name, nargs="?", help=help)
            else:
                assert False, parameter.kind
    args = vars(parser.parse_args())
    basicConfig(level=DEBUG if args["debug"] else INFO)
    try:
        load_config(args["config_file"])
    except ValidationError as e:
        cprint(f"Error validating {args['config_file']}", "light_red")
        errors = e.errors(include_url=False)
        for error in errors:
            cprint(
                f"{error['msg']}: {'.'.join(str(c) for c in error['loc'])}", "light_red"
            )
        exit(1)
    if args["script"] == "server":
        SERVER_COMMANDS[args["service"]]()
        return
    script_dict = {script.__name__: script for script in SCRIPTS}
    script = script_dict[args["script"]]
    varargs: list[Any] = []
    kwargs: dict[str, Any] = {}
    for parameter in signature(script).parameters.values():
        arg = args[parameter.name]
        if parameter.kind == Parameter.KEYWORD_ONLY:
            kwargs[parameter.name] = arg
        else:
            varargs.append(arg)
    script(*varargs, **kwargs)


if __name__ == "__main__":
    main()
