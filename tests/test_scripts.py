from __future__ import annotations
from worker.scripts import setup_git, get_aliases, get_aliases_command
from worker.ssh import SSH
from worker.config import Config
from tempfile import TemporaryDirectory, NamedTemporaryFile
from subprocess import call, run, PIPE, check_call
from os import environ


def test_scripts_aliases_shell_escape(test_config: Config):
    expected = """alias dock="docker-compose build --parallel --no-rm && docker-compose down --remove-orphans -t 0 && docker-compose up -d"
alias deploy="echo -n \\$(git rev-parse HEAD) > .prev.txt && git pull && dock"
alias revert="git reset --hard \\$(cat .prev.txt) && dock"
alias docker-compose="docker compose"
alias abcd="ls"
"""
    actual = run(
        get_aliases_command(get_aliases(test_config["aliases"])),
        shell=True,
        check=True,
        stdout=PIPE,
        text=True,
    ).stdout
    assert actual == expected


def test_scripts_aliases_command(test_config: Config):
    with NamedTemporaryFile() as tmp:
        check_call(
            f'({get_aliases_command(get_aliases(test_config["aliases"]))}) >> {tmp.name}',
            shell=True,
        )
        aliases = run(
            f"shopt -s expand_aliases && source {tmp.name} && alias",
            shell=True,
            stdout=PIPE,
            text=True,
        ).stdout
        for key, value in test_config["aliases"].items():
            assert f"{key}='{value}'" in aliases


def test_scripts_git(remote_server: SSH):
    setup_git(["project"], "127.0.0.1", 2222)
    with TemporaryDirectory() as dir:
        assert (
            call(
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
            == 0
        )


def test_scripts_keys(remote_server: SSH):
    assert (
        call(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "root@127.0.0.1",
                "-p",
                "2222",
                "ls",
            ]
        )
        == 0
    )


def test_scripts_aliases_final(remote_server: SSH):
    assert (
        remote_server.run("shopt -s expand_aliases && source .profile && eval abcd")
        == 0
    )
