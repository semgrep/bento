import logging
import os
from typing import Any, Dict, Optional, Type

import yaml

import bento.constants as constants
import bento.extra
import bento.formatter
from bento.formatter import Formatter
from bento.tool import Tool, ToolContext
from bento.util import echo_error


class Context:
    def __init__(self, base_path: str = ".", config: Optional[Dict[str, Any]] = None):
        self._base_path = base_path
        self._config: Optional[Dict[str, Any]] = None
        if config is not None:
            self._config = config
        self._formatter: Optional[Formatter] = None
        self._tool_inventory: Optional[Dict[str, Type[Tool]]] = None
        self._tools: Optional[Dict[str, Tool]] = None

    @property
    def base_path(self) -> str:
        return self._base_path

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is None:
            self._config = Context._open_config()
        return self._config

    @config.setter
    def config(self, config: Dict[str, Any]) -> None:
        Context._write_config(config)
        self._config = config

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

    def tool_context(self, tool_id: str) -> ToolContext:
        """
        Returns a configured tool's subcontext

        Raises:
            AttributeError: If the requested tool is not configured
        """
        tt = self.config["tools"]
        if tool_id not in tt:
            raise AttributeError(f"{tool_id} not one of {', '.join(tt.keys())}")
        return ToolContext(base_path=self.base_path, config=tt[tool_id])

    @staticmethod
    def _open_config() -> Dict[str, Any]:
        """
        Opens this project's configuration file
        """
        logging.info(
            f"Loading bento configuration from {os.path.abspath(constants.CONFIG_PATH)}"
        )
        with open(constants.CONFIG_PATH) as yaml_file:
            return yaml.safe_load(yaml_file)

    @staticmethod
    def _write_config(config: Dict[str, Any]) -> None:
        """
        Overwrites this project's configuration file
        """
        logging.info(
            f"Writing bento configuration to {os.path.abspath(constants.CONFIG_PATH)}"
        )
        with open(constants.CONFIG_PATH, "w") as yaml_file:
            yaml.safe_dump(config, yaml_file)

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
        for tn in self.config["tools"].keys():
            ti = inventory.get(tn, None)
            if not ti:
                # TODO: Move to display layer
                echo_error(f"No tool named '{tn}' could be found")
                continue
            tools[tn] = ti(self.tool_context(tn))

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
