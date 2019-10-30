import logging
import time
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Type, Union

import attr
import yaml

import bento.extra
import bento.formatter
from bento.formatter import Formatter
from bento.tool import Tool, ToolContext
from bento.util import echo_error


def _clean_path(path: Union[str, Path]) -> Path:
    # The resolve here is important, since flake8 seems to have weird behavior
    # regarding finding unused imports if the path is not fully-resolved.
    return Path(path).resolve()


@attr.s
class Context:
    # The path to the directory that contains the .bento dir and .bento.yml
    # file. Tools will also be run from here.
    base_path: Path = attr.ib(converter=_clean_path)
    _config: Optional[Dict[str, Any]] = attr.ib(default=None)
    _formatter: Optional[Formatter] = attr.ib(init=False, default=None)
    _start: float = attr.ib(init=False, factory=time.time)
    _tool_inventory: Optional[Dict[str, Type[Tool]]] = None
    _tools: Optional[Dict[str, Tool]] = None

    CONFIG_FILE: ClassVar[str] = ".bento.yml"
    RESOURCE_DIR: ClassVar[str] = ".bento"
    LOCAL_RUN_CACHE: ClassVar[str] = ".bento/cache"
    BASELINE_FILE_PATH: ClassVar[str] = ".bento-whitelist.yml"

    @base_path.default
    def _find_base_path(self) -> Path:
        """Find the path to the nearest containing directory with bento config.

        This starts at the current directory, then recurses upwards looking for
        a directory with the necessary config file.

        The returned path is relative to the current working directory, so that
        when printed in log messages and such it looks readable.

        If one isn't found, returns the current working directory. This
        behavior is so that you can construct a Context in a directory that
        doesn't have Bento set up, then use the config_path and such to figure
        out where to do the initialization.

        """
        cwd = Path.cwd()
        for base_path in [cwd, *cwd.parents]:
            if (base_path / self.CONFIG_FILE).is_file():
                return base_path
        return cwd

    @property
    def config_path(self) -> Path:
        return self.base_path / self.CONFIG_FILE

    @property
    def resource_dir(self) -> Path:
        return self.base_path / self.RESOURCE_DIR

    @property
    def local_run_cache(self) -> Path:
        return self.base_path / self.LOCAL_RUN_CACHE

    @property
    def baseline_file_path(self) -> Path:
        return self.base_path / self.BASELINE_FILE_PATH

    def pretty_path(self, path: Path) -> Path:
        try:
            return path.relative_to(self.base_path)
        except ValueError:
            return path

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is None:
            logging.info(
                f"Loading bento configuration from {self.config_path.resolve()}"
            )
            with self.config_path.open() as yaml_file:
                self._config = yaml.safe_load(yaml_file)
        return self._config

    @config.setter
    def config(self, config: Dict[str, Any]) -> None:
        logging.info(f"Writing bento configuration to {self.config_path.resolve()}")
        self._config = config
        with self.config_path.open("w") as yaml_file:
            yaml.safe_dump(config, yaml_file)

    @property
    def formatter(self) -> Formatter:
        if self._formatter is None:
            self._formatter = self._load_formatter()
        return self._formatter

    @property
    def tools(self) -> Dict[str, Tool]:
        """
        Returns all configured tools
        """
        if self._tools is None:
            self._tools = self._load_configured_tools()
        return self._tools

    @property
    def tool_inventory(self) -> Dict[str, Type[Tool]]:
        if self._tool_inventory is None:
            self._tool_inventory = self._load_tool_inventory()
        return self._tool_inventory

    def elapsed(self) -> float:
        return time.time() - self._start

    def tool(self, tool_id: str) -> Tool:
        """
        Returns a specific configured tool

        Raises:
            AttributeError: If the requested tool is not configured
        """
        tt = self.tools
        if tool_id not in tt:
            raise AttributeError(f"{tool_id} not one of {', '.join(tt.keys())}")
        return tt[tool_id]

    def _tool_context(self) -> ToolContext:
        """
        Returns the subcontext for configuring tools.
        """
        self.local_run_cache.mkdir(exist_ok=True, parents=True)
        self.resource_dir.mkdir(exist_ok=True, parents=True)
        return ToolContext(
            base_path=str(self.base_path),
            cache_dir=str(self.local_run_cache),
            resource_dir=str(self.resource_dir),
        )

    def _load_tool_inventory(self) -> Dict[str, Type[Tool]]:
        """
        Loads all tools in the module into a dictionary indexed by tool_id
        """
        all_tools = {}
        for tt in bento.extra.TOOLS:
            tool_id = tt.tool_id()
            all_tools[tool_id] = tt
        logging.debug(f"Known tool IDs are {', '.join(all_tools.keys())}")
        return all_tools

    def _load_configured_tools(self) -> Dict[str, Tool]:
        """
        Returns a list of this project's configured tools
        """
        tools: Dict[str, Tool] = {}
        inventory = self.tool_inventory
        for tn, tool_config in self.config["tools"].items():
            ti = inventory.get(tn, None)
            if not ti:
                # TODO: Move to display layer
                echo_error(f"No tool named '{tn}' could be found")
                continue
            tools[tn] = ti(tool_context=self._tool_context(), config=tool_config)

        return tools

    def _load_formatter(self) -> Formatter:
        """
        Returns this project's configured formatter
        """
        if "formatter" not in self.config:
            return bento.formatter.Stylish()
        else:
            f_class, cfg = next(iter(self.config["formatter"].items()))
            return bento.formatter.for_name(f_class, cfg)
