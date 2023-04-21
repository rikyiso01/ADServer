from worker.scripts import setup_git
from worker.ssh import SSH
from tempfile import TemporaryDirectory
from subprocess import check_call
from os import environ


def test_git(remote_server: SSH):
    setup_git(["project"], "127.0.0.1", 2222)
    with TemporaryDirectory() as dir:
        check_call(
            [
                "git",
                "clone",
                "-b",
                "project",
                "git@127.0.0.1:/opt/git/project.git",
                dir,
            ],
            env={
                "GIT_SSH_COMMAND": "ssh -i tests/test_rsa -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -p 2223",
                **environ,
            },
        )


def test_keys(remote_server: SSH):
    check_call(
        ["ssh", "-o", "StrictHostKeyChecking=no", "root@127.0.0.1", "-p", "2222", "ls"]
    )


def test_alias(remote_server: SSH):
    remote_server.check_call("shopt -s expand_aliases && source .profile && eval abcd")
