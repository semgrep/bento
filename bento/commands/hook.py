import os
import shutil
import stat
import sys

import click
import git

import bento.constants as constants
import bento.git
import bento.tool_runner
from bento.network import post_metrics
from bento.util import echo_error, echo_success


@click.command()
def install_hook() -> None:
    """
    Installs bento as a git pre-commit hook.

    Saves any existing pre-commit hook to .git/hooks/pre-commit.pre-bento and
    runs said hook after bento hook is run.
    """

    def is_bento_precommit(filename: str) -> bool:
        if not os.path.exists(filename):
            return False
        with open(filename) as f:
            lines = f.read()
        return constants.BENTO_TEMPLATE_HASH in lines

    # Get hook path
    repo = bento.git.repo()
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

        post_metrics(bento.metrics.command_metric("install-hook"))
        echo_success(f"Added Bento to your git pre-commit hooks.")
