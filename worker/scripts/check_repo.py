from subprocess import call
from tempfile import TemporaryDirectory
from os import environ
from worker.config import CONFIG
from termcolor import cprint


def check_repo():
    """check if the private key given in the config file can access the github repo"""
    with TemporaryDirectory() as tmp:
        result = (
            call(
                [
                    "git",
                    "clone",
                    CONFIG["git"]["git_repo"],
                    tmp,
                ],
                env={
                    f"GIT_SSH_COMMAND": f"ssh -i {CONFIG['git']['ssh_key']} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -F /dev/null",
                    **environ,
                },
            )
            == 0
        )
        if result:
            cprint("The repo is functioning correctly", "light_green")
        else:
            cprint("Error accessing the repo with the server key", "light_red")
            exit(1)
