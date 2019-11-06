import json
import logging
import shlex
import subprocess
import venv
from abc import abstractmethod
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import click
from packaging.version import InvalidVersion, Version

import bento.tool
from bento.base_context import BaseContext
from bento.util import echo_success


class PythonTool(bento.tool.Tool):
    # On most environments, just "pip" will point to the wrong Python installation
    # Fix by using the virtual environment's python
    PIP_CMD = "python -m pip"

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return cls.project_has_extensions(context, "*.py")

    @classmethod
    @abstractmethod
    def venv_subdir_name(cls) -> str:
        pass

    @property
    def __venv_dir(self) -> Path:
        return self.context.resource_path / self.venv_subdir_name()

    def venv_create(self) -> None:
        """
        Creates a virtual environment for this tool
        """
        if not self.__venv_dir.exists():
            echo_success(f"Creating virtual environment for {self.tool_id()}")
            # If we are already in a virtual environment, venv.create() will fail to install pip,
            # but we probably have virtualenv in the path, so try that first.
            try:
                # Don't litter stdout with virtualenv spam
                subprocess.run(
                    ["virtualenv", self.__venv_dir],
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
            except Exception:
                venv.create(str(self.__venv_dir), with_pip=True)

    def venv_exec(
        self,
        cmd: str,
        env: Dict[str, str] = bento.util.EMPTY_DICT,
        check_output: bool = True,
    ) -> str:
        """
        Executes tool set-up or check within its virtual environment
        """
        wrapped = f". {self.__venv_dir}/bin/activate; {cmd}"
        logging.debug(f"{self.tool_id()}: Running '{wrapped}'")
        v = subprocess.Popen(
            wrapped,
            shell=True,
            cwd=str(self.base_path),
            encoding="utf8",
            executable="/bin/bash",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = v.communicate()
        logging.debug(f"{self.tool_id()}: stderr[:4000]:\n" + stderr[0:4000])
        logging.debug(f"{self.tool_id()}: stdout[:4000]:\n" + stdout[0:4000])
        if check_output and v.returncode != 0:
            raise subprocess.CalledProcessError(
                v.returncode, wrapped, output=stdout, stderr=stderr
            )
        return stdout

    @staticmethod
    def sanitize_arguments(
        arguments: Iterable[str]
    ) -> Tuple[Dict[str, str], List[str]]:
        """
        Sanitizes arguments to be passed into a shell execution.

        Returns (env, args). 'env' should be passed directly to popen's env parameter, and args can
        be included where desired in the command.

        NOTE: In general, we should avoid shell execution altogether. This utility is provided as a
        mechanism to prevent shell injection when such execution is unavoidable (e.g., when operating
        within a Python virtual environment).

        Example:
            cmd = "echo "
            bad_args = ['"foo"; rm -rf /']

            # DON'T DO THIS:
            # subprocess.run(f'{cmd} {" ".join(bad_args)}', shell=True)

            # DO THIS:
            env, clean_args = PythonTool.sanitize_arguments(bad_args)
            subprocess.run(f'{cmd} {" ".join(clean_args)}', env=env, shell=True)

        Returns:
            (dict, str): An environment dictionary, and the new sanitized argument list
        """
        env = {}
        args = []
        for ix, a in enumerate(arguments):
            var = f"SANITIZED_{ix}"
            env[var] = a
            args.append(f'"${var}"')
        return env, args

    def _packages_installed(self, packages: Dict[str, str]) -> bool:
        """Checks whether the given packages are installed.

        The value for each package is the minimum required version."""
        installed: Dict[str, Version] = {}
        for package in json.loads(
            self.venv_exec(f"{PythonTool.PIP_CMD} list --format json")
        ):
            try:
                installed[package["name"]] = Version(package["version"])
            except InvalidVersion:
                # skip it
                pass

        to_install: Dict[str, str] = {}
        for name in packages:
            minimum_version = Version(packages[name])
            if name not in installed or installed[name] < minimum_version:
                to_install[name] = str(minimum_version)

        if to_install:
            click.echo(f"Installing Python packages: {to_install}", err=True)
            return False
        else:
            return True

    def _ignore_param(self) -> str:
        """
        Returns a file exclusion parameter for Python tools
        """
        ignores = (
            shlex.quote(e.path)
            for e in self.context.file_ignores.entries()
            if not e.survives
        )
        return ",".join(ignores)
