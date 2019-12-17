import os
import shutil
import stat
import sys

import click

import bento.constants as constants
import bento.git
import bento.tool_runner
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_error, echo_success


def is_bento_precommit(filename: str) -> bool:
    if not os.path.exists(filename):
        return False
    with open(filename) as f:
        lines = f.read()
    return constants.BENTO_TEMPLATE_HASH in lines


@click.command()
@click.pass_obj
@with_metrics
def install_hook(context: Context) -> None:
    """
    Installs bento as a git pre-commit hook.

    Saves any existing pre-commit hook to .git/hooks/pre-commit.pre-bento and
    runs said hook after bento hook is run.
    """
    import git  # import inside def for performance

    # Get hook path
    repo = bento.git.repo(context.base_path)
    if repo is None:
        echo_error("Not a git project")
        sys.exit(3)

    hook_path = git.index.fun.hook_path("pre-commit", repo.git_dir)

    if is_bento_precommit(hook_path):
        echo_success(f"Bento already installed as a pre-commit hook")
    else:
        legacy_hook_path = f"{hook_path}.pre-bento"
        if os.path.exists(hook_path):
            # If pre-commit hook already exists move it over
            if os.path.exists(legacy_hook_path):
                raise Exception(
                    "There is already a legacy hook. Not sure what to do so just exiting for now."
                )
            else:
                # Check that
                shutil.move(hook_path, legacy_hook_path)

        # Copy pre-commit script template to hook_path
        template_location = os.path.join(
            os.path.dirname(__file__), "../resources/pre-commit.template"
        )
        shutil.copyfile(template_location, hook_path)

        # Make file executable
        original_mode = os.stat(hook_path).st_mode
        os.chmod(hook_path, original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        echo_success(f"Added Bento to your git pre-commit hooks.")


@click.command()
@click.pass_obj
@with_metrics
def uninstall_hook(context: Context) -> None:
    """
    Uninstalls bento as a git pre-commit hook.

    Returns any pre-bento pre-commit hooks that were placed in .git/hooks/pre-commit.pre-bento
    into .git/hooks/pre-commit
    """
    import git  # import inside def for performance

    # Get hook path
    repo = bento.git.repo(context.base_path)
    if repo is None:
        echo_error("Not a git project")
        sys.exit(3)

    hook_path = git.index.fun.hook_path("pre-commit", repo.git_dir)

    if not is_bento_precommit(hook_path):
        echo_error(f"Install hook in {hook_path} is not a bento pre-commit hook")
        sys.exit(3)
    else:
        # Put back legacy hook if exits
        legacy_hook_path = f"{hook_path}.pre-bento"
        if os.path.exists(legacy_hook_path):
            shutil.move(legacy_hook_path, hook_path)
        else:
            os.remove(hook_path)

        echo_success(f"Removed Bento from your git pre-commit hooks.")
