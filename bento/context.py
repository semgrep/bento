import logging
import time
from typing import Dict, Type

import attr

import bento.extra
import bento.formatter
from bento.base_context import BaseContext
from bento.formatter import Formatter
from bento.tool import Tool
from bento.util import echo_error


@attr.s
class Context(BaseContext):
    _formatter = attr.ib(type=Formatter, default=None, init=False)
    _start = attr.ib(type=float, default=time.time(), init=False)
    _tool_inventory = attr.ib(type=Dict[str, Type[Tool]], init=False, default=None)
    _tools = attr.ib(type=Dict[str, Tool], init=False, default=None)

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
            tools[tn] = ti(self)

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
