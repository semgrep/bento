import json
import os
import subprocess
import venv
from abc import abstractmethod
from typing import Dict, Iterable, List, Tuple

from packaging.version import InvalidVersion, Version

import bento.constants
import bento.tool
from bento.util import echo_success


class PythonTool(bento.tool.Tool):
    # On most environments, just "pip" will point to the wrong Python installation
    # Fix by using the virtual environment's python
    PIP_CMD = "python -m pip"

    def matches_project(self) -> bool:
        return self.project_has_extensions("*.py")

    @property
    @abstractmethod
    def venv_subdir(self) -> str:
        """
        Subdirectory inside resource directory where virtual env is located.
        """
        pass

    @property
    def __venv_dir(self) -> str:
        return os.path.join(
            self.base_path, bento.constants.RESOURCE_DIR, self.venv_subdir
        )

    def venv_create(self) -> None:
        """
        Creates a virtual environment for this tool
        """
        if not os.path.exists(self.__venv_dir):
            echo_success(f"Creating virtual environment for {self.tool_id}")
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
                venv.create(self.__venv_dir, with_pip=True)

    def venv_exec(
        self, cmd: str, env: Dict[str, str] = {}, check_output: bool = True
    ) -> str:
        """
        Executes tool set-up or check within its virtual environment
        """
        wrapped = f"source {self.__venv_dir}/bin/activate; {cmd}"
        v = subprocess.Popen(
            wrapped,
            shell=True,
            cwd=self.base_path,
            encoding="utf8",
            executable="/bin/bash",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = v.communicate()
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

        all_installed = True
        for name in packages:
            minimum_version = Version(packages[name])
            if name not in installed:
                echo_success(f"Python package {name} will be installed")
                all_installed = False
            elif installed[name] < minimum_version:
                echo_success(
                    f"Python package {name} will be upgraded (current {installed[name]}, want {minimum_version})"
                )
                all_installed = False
        return all_installed
