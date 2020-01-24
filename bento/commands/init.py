import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Union

import attr
import click
import yaml

import bento.constants as constants
import bento.content.init as content
import bento.git
import bento.tool_runner
from bento.commands.autorun import install_autorun
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_error


def _dim_filename(path: Union[Path, str]) -> str:
    return f"{click.style(str(path), bold=True, dim=True)}"


@attr.s(auto_attribs=True)
class InitCommand(object):
    context: Context

    def _install_config_if_not_exists(self) -> bool:
        """
        Installs .bento.yml if one does not already exist

        :return: whether a config was installed
        """
        config_path = self.context.config_path
        pretty_path = self.context.pretty_path(config_path)
        if not config_path.exists():
            on_done = content.InstallConfig.install.echo(pretty_path)
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
            if not yml["tools"]:
                logging.warning("No tools match this project")
            with config_path.open("w") as config_file:
                yaml.safe_dump(yml, stream=config_file)
            on_done()
            logging.info(f"Created {pretty_path}.")
            return True
        else:
            content.InstallConfig.install.echo(pretty_path, skip=True)
            return False

    def _install_ignore_if_not_exists(self) -> bool:
        """
        Installs .bentoignore if it does not already exist

        :return: whether .bentoignore was created
        """
        pretty_path = self.context.pretty_path(self.context.ignore_file_path)
        if not self.context.ignore_file_path.exists():
            on_done = content.InstallIgnore.install.echo(pretty_path)
            templates_path = Path(os.path.dirname(__file__)) / ".." / "configs"
            shutil.copy(
                templates_path / constants.IGNORE_FILE_NAME,
                self.context.ignore_file_path,
            )

            gitignore_added = False

            # If we're in a git repo with a .gitignore, add it to .bentoignore
            repo = bento.git.repo()
            if repo:
                path_to_gitignore = Path(repo.working_tree_dir) / ".gitignore"
                if path_to_gitignore.exists():
                    include_path = os.path.relpath(
                        path_to_gitignore, self.context.base_path
                    )
                    with self.context.ignore_file_path.open("a") as ignore_file:
                        ignore_file.write(f":include {include_path}\n")
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
            content.InstallIgnore.install.echo(pretty_path, skip=True)
            return False

    def _configure_autorun(self, ctx: click.Context, is_first_run: bool) -> None:
        if is_first_run:
            on_done = content.InstallAutorun.install.echo()
            ctx.invoke(install_autorun, block=True)
            on_done()
        else:
            content.InstallAutorun.install.echo(skip=True)

    def _install_tools(self, clean: bool) -> None:
        """
        Ensures tools are installed

        :param clean: If true, forces tool reinstallation
        """
        content.InstallTools.install.echo()
        if clean:
            content.Clean.tools.echo()
            shutil.rmtree(constants.VENV_PATH, ignore_errors=True)
        runner = bento.tool_runner.Runner(paths=[], install_only=True, use_cache=False)
        tools = self.context.tools.values()
        runner.parallel_results(tools, {})

    def _identify_git(self) -> None:
        repo = bento.git.repo(self.context.base_path)
        if repo is None:
            echo_error(
                "Current directory is not part of a Git project. Bento only works for Git projects."
            )
            sys.exit(3)

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
            content.Identify.failure.echo()
            return
        content.Identify.success.echo(projects)

    def _finish(self) -> None:
        content.Finish.body.echo()

    def run(self, ctx: click.Context, clean: bool) -> None:
        content.Start.banner.echo()

        if sys.stdin.isatty() and sys.stderr.isatty():
            content.Start.confirm.echo(default=True, show_default=False)

        self.context.resource_path.mkdir(exist_ok=True)
        is_first_init = not self.context.config_path.exists()
        # Perform git identification
        self._identify_git()

        # Perform configuration
        self._install_ignore_if_not_exists()
        self._install_config_if_not_exists()
        self._configure_autorun(ctx, is_first_init)

        # Perform project identification
        self._identify_project()

        # Perform initial analysis
        self._install_tools(clean)

        # Message next steps
        self._finish()


@click.command()
@click.pass_context
@click.option(
    "--clean",
    help="Reinstalls tools using a clean installation.",
    is_flag=True,
    default=False,
)
@with_metrics
def init(ctx: click.Context, clean: bool) -> None:
    """
    Autodetects and installs tools.

    Run again after changing tool list in .bento.yml
    """
    context: Context = ctx.obj

    InitCommand(context).run(ctx, clean)
