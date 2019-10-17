import logging
import os
import sys

import click
import yaml

import bento.constants as constants
import bento.tool_runner
from bento.context import Context
from bento.network import post_metrics
from bento.util import echo_error, echo_success


def __install_config_if_not_exists(context: Context) -> None:
    if not os.path.exists(constants.CONFIG_PATH):
        click.echo(f"Creating default configuration at {constants.CONFIG_PATH}")
        with (
            open(os.path.join(os.path.dirname(__file__), "../configs/default.yml"))
        ) as template:
            yml = yaml.safe_load(template)
        for tid, t in context.tool_inventory.items():
            if not t().matches_project():
                del yml["tools"][tid]
        with (open(constants.CONFIG_PATH, "w")) as config_file:
            yaml.safe_dump(yml, stream=config_file)
        echo_success(
            f"Created {constants.CONFIG_PATH}. Please check this file in to source control.\n"
        )


@click.command()
@click.pass_obj
def init(context: Context) -> None:
    """
    Autodetects and installs tools.

    Run again after changing tool list in .bento.yml
    """
    __install_config_if_not_exists(context)

    tools = context.tools.values()
    project_names = sorted(list(set(t.project_name for t in tools)))
    logging.debug(f"Project names: {project_names}")
    if len(project_names) > 2:
        projects = f'{", ".join(project_names[:-2])}, and {project_names[-1]}'
    elif project_names:
        projects = " and ".join(project_names)
    else:
        echo_error("Bento can't identify this project.")
        sys.exit(3)

    click.secho(f"Detected project with {projects}\n", fg="blue", err=True)

    for t in tools:
        t.setup()

    r = bento.git.repo()
    if sys.stdout.isatty() and r:
        ignore_file = os.path.join(r.working_tree_dir, ".gitignore")
        has_ignore = None
        if os.path.exists(ignore_file):
            with open(ignore_file, "r") as fd:
                has_ignore = next(filter(lambda l: l.rstrip() == ".bento/", fd), None)
        if has_ignore is None:
            click.secho(
                "It looks like you're managing this project with git. We recommend adding '.bento/' to your '.gitignore'."
            )
            if click.confirm("  Do you want Bento to do this for you?", default=True):
                with open(ignore_file, "a") as fd:
                    fd.write(
                        "# Ignore bento tool run paths (this line added by `bento init`)\n.bento/"
                    )
                echo_success(
                    "Added '.bento/' to your .gitignore. Please commit your .gitignore.\n"
                )

    echo_success("Bento is initialized on your project.")

    post_metrics(bento.metrics.command_metric("setup"))
