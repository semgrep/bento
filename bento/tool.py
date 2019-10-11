import logging
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Pattern, Set, Type, Union

import bento.util
from bento.parser import Parser
from bento.result import Violation


# Note: for now, every tool *HAS* to directly inherit from this, even if it
# also inherits from JsTool or PythonTool. This is so we can list all tools by
# looking at subclasses of Tool.
class Tool(ABC):
    _base_path: Union[None, str] = None

    @property
    def base_path(self) -> str:
        """Returns the base path from which this tool should run"""
        if self._base_path is None:
            raise AttributeError("base_path is unset")
        return self._base_path

    @base_path.setter
    def base_path(self, bp: str) -> None:
        """Configures this tool's base path"""
        self._base_path = bp

    def parser(self) -> Parser:
        """Returns this tool's parser"""
        return self.parser_type(self.base_path)

    @property
    @abstractmethod
    def parser_type(self) -> Type[Parser]:
        """Returns this tool's parser type"""
        pass

    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Returns this tool's string ID"""
        pass

    @property
    @abstractmethod
    def project_name(self) -> str:
        """Returns this tool's human friendly project name"""
        pass

    @property
    @abstractmethod
    def file_name_filter(self) -> Pattern:
        """Returns a pattern that determines whether a terminal path should be run through this tool"""
        pass

    @abstractmethod
    def setup(self, config: Dict[str, Any]) -> None:
        """
        Runs all code necessary to install this tool

        Code runs inside virtual environment.

        Parameters:
            config (dict): The tool configuration

        Raises:
            CalledProcessError: If setup fails
        """
        pass

    @abstractmethod
    def run(self, config: Dict[str, Any], files: Iterable[str]) -> str:
        """
        Runs this tool, returning its standard output

        Code runs inside virtual environment.

        Parameters:
            config (dict): The tool configuration

        Raises:
            CalledProcessError: If execution fails
        """
        pass

    @abstractmethod
    def matches_project(self) -> bool:
        """
        Returns true if and only if this project should use this tool
        """
        pass

    def project_has_extensions(self, *extensions: str, extra: List[str] = []) -> bool:
        patterns = [["-name", e] for e in extensions]
        args = patterns[0] + [a for p in patterns[1:] for a in ["-o"] + p]
        cmdA = ["find", ".", "("] + args + [")"] + extra
        cmdB = ["head", "-n", "1"]
        # We want to run "find", but terminate after a single file is returned
        logging.debug(f"Running {' '.join(cmdA)} | {' '.join(cmdB)}")
        procA = subprocess.Popen(cmdA, cwd=self.base_path, stdout=subprocess.PIPE)
        procB = subprocess.Popen(
            cmdB,
            cwd=self.base_path,
            stdin=procA.stdout,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        procA.stdout.close()
        procB.wait()
        res = next(procB.stdout, None)
        return res is not None

    def filter_paths(self, config: Dict[str, Any], paths: Iterable[str]) -> Set[str]:
        """
        Filters a list of paths to those that should be analyzed by this tool

        In it's default behavior, this method:
          - Filters terminal paths (files) that match file_name_filter.
          - Filters non-terminal paths (directories) that include at least one matching path.

        Parameters:
            config (dict): The tool configuration
            paths (list): List of candidate paths

        Returns:
            A set of valid paths
        """

        def add_path(out: Set[str], p: str) -> None:
            if os.path.isdir(p):
                # Adds path if any file matches filter
                for r, _, files in os.walk(p):
                    for f in files:
                        if self.file_name_filter.match(f):
                            out.add(p)
                            return
            elif self.file_name_filter.match(p):
                out.add(p)

        out: Set[str] = set()
        for p in paths:
            add_path(out, p)

        return out

    def exec(self, command: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """
        Delegates to subprocess.run() on this tool's base path

        Raises:
            CalledProcessError: If execution fails and check is True
        """
        new_args: Dict[str, Any] = {"cwd": self.base_path, "encoding": "utf8"}
        new_args.update(kwargs)
        return subprocess.run(command, **new_args)

    def results(
        self, config: Dict[str, Any], paths: Optional[Iterable[str]] = None
    ) -> List[Violation]:
        """
        Runs this tool, returning all identified violations

        Code runs inside virtual environment.

        Parameters:
            config (dict): The tool configuration
            paths (list or None): If defined, an explicit list of paths to run on

        Raises:
            CalledProcessError: If execution fails
        """
        if paths is None:
            paths = [self.base_path]
        paths = self.filter_paths(config, paths)

        if paths:
            raw = self.run(config, paths)
            try:
                violations = self.parser().parse(raw)
            except Exception:
                raise Exception(f"Could not parse output of '{self.tool_id}':\n{raw}")
            ignore_set = set(config.get("ignore", []))
            filtered = [v for v in violations if v.check_id not in ignore_set]
            return filtered
        else:
            return []


def for_name(name: str, base_path: str) -> Tool:
    """
    Reflectively instantiates a tool from a python identifier

    E.g.
      for_name("bento.extra.eslint.EslintTool", "path/to/repo")
    returns a new instance of EslintTool

    Parameters:
        name (str): The tool name, as a python fully qualified identifier
    """
    tool = bento.util.for_name(name)()
    tool.base_path = base_path
    return tool
