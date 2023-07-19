from __future__ import annotations
from worker.config import CONFIG, get_ssh_key


def check_keys() -> int:
    ok = True
    for user in CONFIG["sshkeys"]["github_users"]:
        if not get_ssh_key(user):
            print(user, "has no ssh keys")
            ok = False
    return 0 if ok else 1
