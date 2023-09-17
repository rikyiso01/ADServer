from subprocess import call
from tempfile import TemporaryDirectory
from os import environ
from worker.config import get_config
from termcolor import cprint


def check_repo():
    """Check if the private key given in the config file can access the github repo"""
    config = get_config()
    with TemporaryDirectory() as tmp:
        result = (
            call(
                [
                    "git",
                    "clone",
                    config.git.git_repo,
                    tmp,
                ],
                env={
                    f"GIT_SSH_COMMAND": f"ssh -i {config.git.ssh_key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -F /dev/null",
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
