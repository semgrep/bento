import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union

import click
import yaml

import bento.git
import bento.tool_runner
from bento.commands.archive import archive
from bento.commands.check import check
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import (
    ANSI_WIDTH,
    LEADER_CHAR,
    PRINT_WIDTH,
    echo_box,
    echo_error,
    echo_newline,
    echo_progress,
    echo_warning,
    echo_wrap,
    wrap,
)

FNAME_STATUS_EXTRA = (
    2 * ANSI_WIDTH
)  # Extra print width for progress bars with filenames


def _dim_filename(path: Union[Path, str]) -> str:
    return f"{click.style(str(path), bold=True, dim=True)}"


def _query_gitignore_update(context: Context) -> Optional[Path]:
    """
    Determines if gitignore should be updated by init

    Requirements:
    - Interactive terminal
    - Git project
    - .gitignore exists
    - bento/ not in .gitignore
    - User agrees

    :return: The path to update, or None if no update should occur
    """
    r = bento.git.repo(context.base_path)
    if sys.stderr.isatty() and sys.stdin.isatty() and r:
        ignore_file = Path(r.working_tree_dir) / ".gitignore"
        has_ignore = None
        if ignore_file.exists():
            with ignore_file.open("r") as fd:
                has_ignore = next(filter(lambda l: l.rstrip() == ".bento/", fd), None)
        if has_ignore is None:
            confirm_text = wrap(
                f"""Some Bento files should be excluded from version control.
Should Bento append them to your {click.style('.gitignore?', bold=True)}"""
            )
            if click.confirm(confirm_text, default=True, err=True):
                echo_newline()
                return ignore_file
            echo_newline()
    return None


def _install_config_if_not_exists(context: Context) -> bool:
    """
    Installs .bento.yml if one does not already exist

    :return: whether a config was installed
    """
    config_path = context.config_path
    pretty_path = context.pretty_path(config_path)
    progress_text = f"Creating default configuration at {_dim_filename(pretty_path)}"
    if not config_path.exists():
        on_done = echo_progress(progress_text, extra=FNAME_STATUS_EXTRA)
        with (
            open(os.path.join(os.path.dirname(__file__), "../configs/default.yml"))
        ) as template:
            yml = yaml.safe_load(template)
        for tid, tool in context.tool_inventory.items():
            if not tool.matches_project(context) and tid in yml["tools"]:
                del yml["tools"][tid]
        logging.debug(
            f"Matching tools for this project: {', '.join(yml['tools'].keys())}"
        )
        if yml["tools"]:
            with config_path.open("w") as config_file:
                yaml.safe_dump(yml, stream=config_file)
            on_done()
            logging.info(f"Created {pretty_path}.")
            return True
        else:
            logging.warning("No tools match this project")
            echo_error("Bento can't identify this project.")
            sys.exit(3)
    else:
        echo_progress(progress_text, extra=FNAME_STATUS_EXTRA, skip=True)
        return False


def _install_ignore_if_not_exists(context: Context) -> bool:
    """
    Installs .bentoignore if it does not already exist

    :return: whether .bentoignore was created
    """
    pretty_path = context.pretty_path(context.ignore_file_path)
    progress_text = f"Creating default ignore file at {_dim_filename(pretty_path)}"
    if not context.ignore_file_path.exists():
        on_done = echo_progress(progress_text, extra=FNAME_STATUS_EXTRA)
        templates_path = Path(os.path.dirname(__file__)) / ".." / "configs"
        shutil.copy(templates_path / ".bentoignore", context.ignore_file_path)

        gitignore_added = False

        # If we're in a git repo with a .gitignore, add it to .bentoignore
        repo = bento.git.repo()
        if repo:
            path_to_gitignore = (
                Path(os.path.relpath(repo.working_tree_dir, context.base_path))
                / ".gitignore"
            )
            if path_to_gitignore.exists():
                with context.ignore_file_path.open("a") as ignore_file:
                    ignore_file.write(f":include {path_to_gitignore}\n")
                gitignore_added = True

        # Otherwise, add the contents of configs/extra-ignore-patterns
        if not gitignore_added:
            with (templates_path / "extra-ignore-patterns").open() as extras:
                with context.ignore_file_path.open("a") as ignore_file:
                    for e in extras:
                        ignore_file.write(e)

        on_done()
        logging.info(f"Created {pretty_path}.")
        return True
    else:
        echo_progress(progress_text, extra=FNAME_STATUS_EXTRA, skip=True)
        return False


def _update_gitignore_if_necessary(ignore_path: Optional[Path]) -> None:
    """Adds bento patterns to project .gitignore if _query_gitignore_update returned a Path"""
    progress_text = f"Updating {_dim_filename('.gitignore')}"
    if ignore_path:
        on_done = echo_progress(progress_text, extra=FNAME_STATUS_EXTRA)
        with ignore_path.open("a") as fd:
            fd.write(
                "\n# Ignore bento tool run paths (this line added by `bento init`)\n.bento/\n"
            )
        on_done()
        logging.info("Added '.bento/' to your .gitignore.")
    else:
        echo_progress(progress_text, extra=FNAME_STATUS_EXTRA, skip=True)


def _maybe_clean_tools(context: Context, clean: bool) -> None:
    """If clean flag is passed, cleans tool installation"""
    if clean:
        echo_warning(f"Reinstalling tools due to passed --clean flag\n")
        subprocess.run(["rm", "-r", context.resource_path], check=True)


def _identify_project(context: Context) -> None:
    """Identifies this project"""
    # echo_box("Project Identification")
    echo_newline()
    tools = context.tools.values()
    project_names = sorted(list({t.project_name for t in tools}))
    logging.debug(f"Project names: {project_names}")
    if len(project_names) > 2:
        projects = f'{", ".join(project_names[:-1])}, and {project_names[-1]}'
    elif project_names:
        projects = " and ".join(project_names)
    else:
        echo_error("Bento can't identify this project.")
        sys.exit(3)
    click.secho(f"Detected project with {click.style(projects, bold=True)}\n", err=True)


def _run_check(ctx: click.Context, clean: bool, pager: bool) -> bool:
    """
    Runs bento check if user agrees to prompt

    :return: If there were findings
    """
    context: Context = ctx.obj

    if clean and context.baseline_file_path.exists():
        echo_warning("Removing archive due to passed --clean flag.\n")
        context.baseline_file_path.unlink()

    if context.baseline_file_path.exists():
        click.secho("Bento archive is already configured on this project.", err=True)
    else:
        if sys.stderr.isatty() and sys.stdin.isatty():
            if click.confirm(
                "Analyze this project for the first time?", default=True, err=True
            ):
                try:
                    echo_box("Bento Check")
                    ctx.invoke(check, formatter=("histo",), pager=pager)
                except SystemExit as ex:
                    if ex.code >= 3:
                        raise ex
                    return True
        else:
            echo_warning("Skipping project analysis due to noninteractive terminal.")

    return False


def _next_steps(diffs_created: bool) -> None:
    fill_width = PRINT_WIDTH - 40
    click.secho(
        f"""
To use Bento:
  {click.style('view archived results'.ljust(fill_width, LEADER_CHAR) + " $", dim=True)} {click.style('bento check --show-all')}
  {click.style('check a specific path'.ljust(fill_width, LEADER_CHAR)+ " $", dim=True)} {click.style('bento check [PATH]')}
  {click.style('disable a check'.ljust(fill_width, LEADER_CHAR)+ " $", dim=True)} {click.style('bento disable check [TOOL] [CHECK]')}
  {click.style('get help about a command'.ljust(fill_width, LEADER_CHAR)+ " $", dim=True)} {click.style('bento [COMMAND] --help')}
""",
        err=True,
    )

    if sys.stdin.isatty() and sys.stderr.isatty():
        click.prompt(
            click.style("Press ENTER to finalize installation"),
            default="",
            hide_input=True,
            show_default=False,
            err=True,
        )

    echo_box("Thank You")
    git_commit_cmd = click.style(
        "git add .gitignore .bento?* && git commit -m 'Add Bento to project'", bold=True
    )
    click.secho("Bento is initialized!\n", err=True)

    if diffs_created:
        click.secho(f"Please add Bento to version control:\n", err=True, dim=True)
        click.secho(f"  $ {git_commit_cmd}\n", err=True)

    echo_wrap(
        f"Help and feedback: {click.style('Reach out to us at support@r2c.dev or file an issue on GitHub. We’d love to hear from you!', dim=True)}"
    )
    click.secho("", err=True)
    echo_wrap(
        f"Community: {click.style('Join #bento on our community Slack. Get support, talk with other users, and share feedback.', dim=True)}"
    )
    click.secho("", err=True)
    echo_wrap(
        f"From all of us at r2c, thank you for trying Bento! We can’t wait to hear what you think."
    )
    echo_newline()


def _run_archive(ctx: click.Context) -> None:
    """
    Runs bento archive if user agrees to prompt

    :return:
    """
    echo_box("Bento Archive")
    ctx.invoke(archive, show_bars=False)


@click.command()
@click.pass_context
@click.option(
    "--clean",
    help="Reinstalls tools using a clean installation.",
    is_flag=True,
    default=False,
)
@click.option(
    "--pager/--no-pager",
    help="Send long output through a pager. This should be disabled when used as an integration (e.g. with an editor).",
    default=True,
)
@with_metrics
def init(ctx: click.Context, clean: bool, pager: bool = True) -> None:
    """
    Autodetects and installs tools.

    Run again after changing tool list in .bento.yml
    """
    context: Context = ctx.obj

    echo_box("Bento Initialization")

    # Ask any necessary pre-install questions
    gitignore_path = _query_gitignore_update(context)

    # Perform configuration
    bentoignore_created = _install_ignore_if_not_exists(context)
    config_created = _install_config_if_not_exists(context)
    _update_gitignore_if_necessary(gitignore_path)

    # Perform project identification
    _identify_project(context)

    # Perform initial analysis
    _maybe_clean_tools(context, clean)
    has_findings = _run_check(ctx, clean, pager)
    if has_findings:
        _run_archive(ctx)

    # Message next steps
    diffs_created = (
        gitignore_path is not None
        or bentoignore_created
        or config_created
        or has_findings
    )
    _next_steps(diffs_created)
