import getpass
import itertools
import os
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional, Tuple

import bento.git
from bento.violation import Violation


def __hash_sha256(data: Optional[str]) -> Optional[str]:
    """ Get SHA256 of data
    """
    if data is None:
        return None
    return sha256(data.encode()).hexdigest()


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


def get_user_uuid() -> Optional[str]:
    """
    Returns the user uuid

    If this is a git repo, returns a hash of the git email; otherwise
    returns a hash of the system-specific user login
    """
    git_email = bento.git.user_email()
    if git_email:
        return __hash_sha256(git_email)
    else:
        return __hash_sha256(getpass.getuser())


def violations_to_metrics(
    tool_id: str, violations: List[Violation], ignores: List[str]
) -> List[Dict[str, Any]]:
    git_url = __hash_sha256(bento.git.url())
    git_commit = bento.git.commit()
    user = get_user_uuid()
    return [
        {
            "tool": tool_id,
            "timestamp": str(datetime.utcnow().isoformat("T")),
            "repository": git_url,
            "commit": git_commit,
            "user": user,
            "ignored_rules": ignores,
            **aggregates,
        }
        for aggregates in __get_aggregate_violations(violations)
    ]


def command_metric(
    command: str,
    command_kwargs: Dict[str, Any],
    exit_code: int,
    duration: float,
    exception: Optional[Exception],
) -> List[Dict[str, Any]]:
    d = {
        "timestamp": str(datetime.utcnow().isoformat("T")),
        "duration": duration,
        "exit_code": exit_code,
        "repository": __hash_sha256(bento.git.url()),
        "hash_of_commit": __hash_sha256(bento.git.commit()),
        "user": get_user_uuid(),
        "command": command,
        "command_kwargs": command_kwargs,
        "is_ci": bool(os.environ.get("CI", False)),
    }
    if exception is not None:
        d["exception"] = str(exception)
    return [d]
