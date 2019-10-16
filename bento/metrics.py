import configparser
import getpass
import itertools
import os
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional, Tuple

import git
import git.exc

from bento.violation import Violation


def __get_git_repo(dirPath: str = os.getcwd()) -> Optional[git.Repo]:
    try:
        r = git.Repo(dirPath, search_parent_directories=True)
        return r
    except git.exc.InvalidGitRepositoryError:
        return None


# N.B. See https://stackoverflow.com/a/42613047
def __get_git_user_email(dirPath: str = os.getcwd()) -> Optional[str]:
    r = __get_git_repo(dirPath)
    if r is None:
        return None
    try:
        return r.config_reader().get_value("user", "email")
    except configparser.NoSectionError:
        return None


def __hash_sha256(data: str) -> str:
    """ Get SHA256 of data
    """
    return sha256(data.encode()).hexdigest()


def __get_git_url(dirPath: str = os.getcwd()) -> Optional[str]:
    """Get remote.origin.url for git dir at dirPath"""
    r = __get_git_repo(dirPath)
    if r and r.remotes and "origin" in r.remotes:
        return __hash_sha256(r.remotes.origin.url)
    else:
        return None


def __get_git_commit(dirPath: str = os.getcwd()) -> Optional[str]:
    """Get head commit for git dir at dirPath"""
    r = __get_git_repo(dirPath)
    if r is None:
        return None
    return str(r.head.commit)


def __get_filtered_violation_count(violations: Iterable[Violation]) -> int:
    return sum(1 for v in violations if v.filtered)


def __get_aggregate_violations(violations: List[Violation]) -> List[Dict[str, Any]]:
    """Returns count of violation per file, per check_id"""

    def grouping(v: Violation) -> Tuple[str, str]:
        return (v.path, v.check_id)

    out = []
    for k, v in itertools.groupby(sorted(violations, key=grouping), grouping):
        p, rid = k
        out.append(
            {
                "path_hash": __hash_sha256(p),
                "check_id_hash": __hash_sha256(rid),
                "check_id": rid,
                "count": sum(1 for _ in v),
                "filtered_count": __get_filtered_violation_count(v),
            }
        )
    return out


def get_user_uuid() -> str:
    """
    Returns the user uuid

    If this is a git repo, returns a hash of the git email; otherwise
    returns a hash of the system-specific user login
    """
    git_email = __get_git_user_email(os.getcwd())
    if git_email:
        return __hash_sha256(git_email)
    else:
        return __hash_sha256(getpass.getuser())


def violations_to_metrics(
    tool_id: str, violations: List[Violation], ignores: List[str]
) -> List[Dict[str, Any]]:
    return [
        {
            "tool": tool_id,
            "timestamp": str(datetime.utcnow().isoformat("T")),
            "repository": __get_git_url(),
            "commit": __get_git_commit(),
            "user": get_user_uuid(),
            "ignored_rules": ignores,
            **aggregates,
        }
        for aggregates in __get_aggregate_violations(violations)
    ]


def command_metric(command: str) -> List[Dict[str, Any]]:
    return [
        {
            "timestamp": str(datetime.utcnow().isoformat("T")),
            "repository": __get_git_url(),
            "commit": __get_git_commit(),
            "user": get_user_uuid(),
            "command": command,
        }
    ]
