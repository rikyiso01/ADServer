from __future__ import annotations
from worker.config import get_config, get_ssh_key
from sys import exit


def check_keys():
    """Check if all the team's members have uploaded at least one ssh key on Github"""
    config = get_config()
    ok = True
    for user in config.sshkeys.github_users:
        if not get_ssh_key(user).unwrap():
            print(user, "has no ssh keys")
            ok = False
    if not ok:
        exit(1)
