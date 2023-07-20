from __future__ import annotations
from worker.config import CONFIG, get_ssh_key


def check_keys():
    """check if all the team's members have uploaded at least one ssh key on Github"""
    ok = True
    for user in CONFIG["sshkeys"]["github_users"]:
        if not get_ssh_key(user):
            print(user, "has no ssh keys")
            ok = False
    if not ok:
        exit(1)
