import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Union

import attr
import click
import yaml

import bento.constants as constants
import bento.git
import bento.tool_runner
from bento.commands.archive import archive
from bento.commands.check import check
from bento.context import Context
from bento.decorators import with_metrics
from bento.renderer import Renderer


def _dim_filename(path: Union[Path, str]) -> str:
    return f"{click.style(str(path), bold=True, dim=True)}"


@attr.s(auto_attribs=True)
class InitCommand(object):
    renderer = Renderer(constants.INIT_CONTENT_PATH)
    context: Context

    def _query_gitignore_update(self) -> Optional[Path]:
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
        r = bento.git.repo(self.context.base_path)
        if sys.stderr.isatty() and sys.stdin.isatty() and r:
            ignore_file = Path(r.working_tree_dir) / ".gitignore"
            has_ignore = None
            if ignore_file.exists():
                with ignore_file.open("r") as fd:
                    has_ignore = next(
                        filter(lambda l: l.rstrip() == ".bento/", fd), None
                    )
            if has_ignore is None:
                if self.renderer.echo("update-gitignore", "confirm"):
                    self.renderer.echo("update-gitignore", "confirm-yes")
                    return ignore_file
                else:
                    self.renderer.echo("update-gitignore", "confirm-no")
        return None

    def _install_config_if_not_exists(self) -> bool:
        """
        Installs .bento.yml if one does not already exist

        :return: whether a config was installed
        """
        config_path = self.context.config_path
        pretty_path = self.context.pretty_path(config_path)
        if not config_path.exists():
            on_done: Callable[[], None] = self.renderer.echo(
                "install-config", "install", args=[pretty_path]
            )
            with (
                open(os.path.join(os.path.dirname(__file__), "../configs/default.yml"))
            ) as template:
                yml = yaml.safe_load(template)
            for tid, tool in self.context.tool_inventory.items():
                if not tool.matches_project(self.context) and tid in yml["tools"]:
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
                self.renderer.echo("install-config", "error")
                sys.exit(3)
        else:
            self.renderer.echo(
                "install-config", "install", args=[pretty_path], skip=True
            )
            return False

    def _install_ignore_if_not_exists(self) -> bool:
        """
        Installs .bentoignore if it does not already exist

        :return: whether .bentoignore was created
        """
        pretty_path = self.context.pretty_path(self.context.ignore_file_path)
        if not self.context.ignore_file_path.exists():
            on_done = self.renderer.echo(
                "install-ignore", "install", args=[pretty_path]
            )
            templates_path = Path(os.path.dirname(__file__)) / ".." / "configs"
            shutil.copy(templates_path / ".bentoignore", self.context.ignore_file_path)

            gitignore_added = False

            # If we're in a git repo with a .gitignore, add it to .bentoignore
            repo = bento.git.repo()
            if repo:
                path_to_gitignore = (
                    Path(os.path.relpath(repo.working_tree_dir, self.context.base_path))
                    / ".gitignore"
                )
                if path_to_gitignore.exists():
                    with self.context.ignore_file_path.open("a") as ignore_file:
                        ignore_file.write(f":include {path_to_gitignore}\n")
                    gitignore_added = True

            # Otherwise, add the contents of configs/extra-ignore-patterns
            if not gitignore_added:
                with (templates_path / "extra-ignore-patterns").open() as extras:
                    with self.context.ignore_file_path.open("a") as ignore_file:
                        for e in extras:
                            ignore_file.write(e)

            on_done()
            logging.info(f"Created {pretty_path}.")
            return True
        else:
            self.renderer.echo(
                "install-ignore", "install", args=[pretty_path], skip=True
            )
            return False

    def _update_gitignore_if_necessary(self, ignore_path: Optional[Path]) -> None:
        """Adds bento patterns to project .gitignore if _query_gitignore_update returned a Path"""
        if ignore_path:
            on_done = self.renderer.echo("update-gitignore", "update")
            with ignore_path.open("a") as fd:
                fd.write(
                    "\n# Ignore bento tool run paths (this line added by `bento init`)\n.bento/\n"
                )
            on_done()
            logging.info("Added '.bento/' to your .gitignore.")
        else:
            self.renderer.echo("update-gitignore", "update", skip=True)

    def _maybe_clean_tools(self, clean: bool) -> None:
        """If clean flag is passed, cleans tool installation"""
        if clean:
            self.renderer.echo("clean", "tools")
            subprocess.run(["rm", "-r", self.context.resource_path], check=True)

    def _identify_project(self) -> None:
        """Identifies this project"""
        tools = self.context.tools.values()
        project_names = sorted(list({t.project_name for t in tools}))
        logging.debug(f"Project names: {project_names}")
        if len(project_names) > 2:
            projects = f'{", ".join(project_names[:-1])}, and {project_names[-1]}'
        elif project_names:
            projects = " and ".join(project_names)
        else:
            self.renderer.echo("identify", "failure")
            sys.exit(3)
        self.renderer.echo("identify", "success", args=[projects])

    def _run_check(self, ctx: click.Context, clean: bool, pager: bool) -> bool:
        """
        Runs bento check if user agrees to prompt

        :return: If there were findings
        """
        if clean and self.context.baseline_file_path.exists():
            self.renderer.echo("clean", "check")
            self.context.baseline_file_path.unlink()

        if self.context.baseline_file_path.exists():
            self.renderer.echo("check", "unnecessary")
        else:
            if sys.stderr.isatty() and sys.stdin.isatty():
                if self.renderer.echo("check", "prompt"):
                    try:
                        self.renderer.echo("check", "header")
                        ctx.invoke(check, formatter=("histo",), pager=pager)
                    except SystemExit as ex:
                        if ex.code >= 3:
                            raise ex
                        return True
            else:
                self.renderer.echo("check", "noninteractive")

        return False

    def _next_steps(self, diffs_created: bool) -> None:
        if sys.stdin.isatty() and sys.stderr.isatty():
            self.renderer.echo("next-steps", "prompt")

        self.renderer.echo("next-steps", "body")

        if diffs_created:
            self.renderer.echo("diffs-added")

        if sys.stdin.isatty() and sys.stderr.isatty():
            self.renderer.echo("finish-init")

        self.renderer.echo("thank-you")

    def _run_archive(self, ctx: click.Context) -> None:
        """
        Runs bento archive if user agrees to prompt

        :return:
        """
        self.renderer.echo("run-archive", "pre")
        ctx.invoke(archive, show_bars=False)
        self.renderer.echo("run-archive", "post")

    def run(self, ctx: click.Context, clean: bool, pager: bool = True) -> None:
        self.renderer.echo("run-all")

        # Ask any necessary pre-install questions
        gitignore_path = self._query_gitignore_update()

        # Perform configuration
        bentoignore_created = self._install_ignore_if_not_exists()
        config_created = self._install_config_if_not_exists()
        self._update_gitignore_if_necessary(gitignore_path)

        # Perform project identification
        self._identify_project()

        # Perform initial analysis
        self._maybe_clean_tools(clean)
        has_findings = self._run_check(ctx, clean, pager)
        if has_findings:
            self._run_archive(ctx)

        # Message next steps
        diffs_created = (
            gitignore_path is not None
            or bentoignore_created
            or config_created
            or has_findings
        )
        self._next_steps(diffs_created)


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
    InitCommand(context).run(ctx, clean, pager)
