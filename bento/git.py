import configparser
import os
from typing import Optional

import git
import git.exc


def repo() -> Optional[git.Repo]:
    try:
        r = git.Repo(os.getcwd(), search_parent_directories=True)
        return r
    except git.exc.InvalidGitRepositoryError:
        return None


# N.B. See https://stackoverflow.com/a/42613047
def user_email() -> Optional[str]:
    r = repo()
    if r is None:
        return None
    try:
        return r.config_reader().get_value("user", "email")
    except configparser.NoSectionError:
        return None
    except configparser.NoOptionError:
        return None


def url() -> Optional[str]:
    """Get remote.origin.url for git dir at dirPath"""
    r = repo()
    if r and r.remotes and "origin" in r.remotes:
        return r.remotes.origin.url
    else:
        return None


def commit() -> Optional[str]:
    """Get head commit for git dir at dirPath"""
    r = repo()
    if r is None:
        return None
    return str(r.head.commit)
