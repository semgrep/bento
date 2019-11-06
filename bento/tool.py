import logging
import os
import subprocess
from abc import ABC, abstractmethod
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Set, Type, TypeVar

import attr

from bento.base_context import BaseContext
from bento.parser import Parser
from bento.result import Violation

ToolT = TypeVar("ToolT", bound="Tool")


# Note: for now, every tool *HAS* to directly inherit from this, even if it
# also inherits from JsTool or PythonTool. This is so we can list all tools by
# looking at subclasses of Tool.
@attr.s
class Tool(ABC):
    context = attr.ib(type=BaseContext)

    @property
    def base_path(self) -> Path:
        """Returns the base path from which this tool should run"""
        return self.context.base_path

    @property
    def config(self) -> Dict[str, Any]:
        """Returns this tool's configuration"""
        return self.context.config["tools"][self.tool_id()]

    def parser(self) -> Parser:
        """Returns this tool's parser"""
        return self.parser_type(self.base_path)

    @property
    @abstractmethod
    def parser_type(self) -> Type[Parser]:
        """Returns this tool's parser type"""
        pass

    @classmethod
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
    def setup(self) -> None:
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
    def run(self, files: Iterable[str]) -> str:
        """
        Runs this tool, returning its standard output

        Code runs inside virtual environment.

        Parameters:
            config (dict): The tool configuration

        Raises:
            CalledProcessError: If execution fails
        """
        pass

    @classmethod
    @abstractmethod
    def matches_project(cls, context: BaseContext) -> bool:
        """
        Returns true if and only if this project should use this tool
        """
        pass

    @classmethod
    def project_has_extensions(cls, context: BaseContext, *extensions: str) -> bool:
        """
        Returns true iff any unignored files matches at least one extension
        """
        file_matches = (
            fnmatch(e.path, ext)
            for e in context.file_ignores.entries()
            if e.survives
            for ext in extensions
        )
        return any(file_matches)

    def filter_paths(self, paths: Iterable[str]) -> Set[str]:
        """
        Filters a list of paths to those that should be analyzed by this tool

        In it's default behavior, this method:
          - Filters terminal paths (files) that match file_name_filter.
          - Filters non-terminal paths (directories) that include at least one matching path.

        Parameters:
            paths (list): List of candidate paths

        Returns:
            A set of valid paths
        """

        def add_path(out: Set[str], p: str) -> None:
            if os.path.isdir(p):
                # Adds path if any file matches filter
                for _, _, files in os.walk(p):
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

    def execute(self, command: List[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """
        Delegates to subprocess.run() on this tool's base path

        Raises:
            CalledProcessError: If execution fails and check is True
        """
        new_args: Dict[str, Any] = {"cwd": self.base_path, "encoding": "utf8"}
        new_args.update(kwargs)
        logging.debug(f"{self.tool_id()}: Running '{' '.join(command)}'")
        res = subprocess.run(command, **new_args)
        return res

    def results(self, paths: Optional[Iterable[str]] = None) -> List[Violation]:
        """
        Runs this tool, returning all identified violations

        Code runs inside virtual environment.

        Before running tool, checks local RunCache for cached tool output and skips
        if said output is still usable

        Parameters:
            paths (list or None): If defined, an explicit list of paths to run on

        Raises:
            CalledProcessError: If execution fails
        """
        if paths is None:
            paths = [str(self.base_path)]
        paths = self.filter_paths(paths)

        if paths:
            logging.debug(f"Checking for local cache for {self.tool_id}")
            raw = self.context.cache.get(self.tool_id(), paths)
            if raw is None:
                logging.debug(f"Cache entry invalid for {self.tool_id}. Running Tool.")
                raw = self.run(paths)
                self.context.cache.put(self.tool_id(), paths, raw)

            try:
                violations = self.parser().parse(raw)
            except Exception as e:
                raise Exception(
                    f"Could not parse output of '{self.tool_id()}':\n{raw}", e
                )
            ignore_set = set(self.config.get("ignore", []))
            filtered = [v for v in violations if v.check_id not in ignore_set]
            return filtered
        else:
            return []
