from typing import Annotated

from result import Err
from worker.destructivefarm import (
    destructivefarm,
    destructivefarm_check,
)
from worker.caronte import caronte, caronte_check
from worker.utils import add_sigterm
from worker.worker import worker, worker_check
from worker.scripts.setup_git import setup_git
from worker.scripts.setup_keys import setup_keys
from worker.scripts.autosetup import autosetup
from worker.scripts.status import status
from worker.scripts.check_keys import check_keys
from worker.scripts.check_repo import check_repo
from worker.config import load_config
from logging import basicConfig, INFO, DEBUG
from termcolor import cprint
from typer import Option, Typer

SCRIPTS = [setup_git, setup_keys, autosetup, status, check_keys, check_repo]
SERVER_COMMANDS = [
    caronte,
    caronte_check,
    destructivefarm,
    destructivefarm_check,
    worker,
    worker_check,
]
typer = Typer()
for script in SCRIPTS:
    _ = typer.command()(script)
subtyper = Typer()
for command in SERVER_COMMANDS:
    _ = subtyper.command()(command)

typer.add_typer(subtyper, name="server", help="Commands used by the containers")


@typer.callback()
def main(
    config_file: Annotated[str, Option(help="Configuration file path")] = "config.toml",
    debug: Annotated[bool, Option(help="Enable more verbose logs")] = False,
):
    basicConfig(level=DEBUG if debug else INFO)
    result = load_config(config_file)
    if isinstance(result, Err):
        cprint(f"Error validating {config_file}", "light_red")
        errors = result.err_value.errors(include_url=False)
        for error in errors:
            cprint(
                f"{error['msg']}: {'.'.join(str(c) for c in error['loc'])}", "light_red"
            )
        exit(1)


if __name__ == "__main__":
    add_sigterm()
    typer()
