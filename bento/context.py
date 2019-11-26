import logging
import time
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type

import attr

import bento.extra
import bento.formatter
from bento.base_context import BaseContext
from bento.formatter import Formatter
from bento.tool import Tool
from bento.util import echo_error


@attr.s
class Context(BaseContext):
    _formatters = attr.ib(type=List[Formatter], default=None, init=False)
    _start = attr.ib(type=float, default=time.time(), init=False)
    _user_start = attr.ib(type=float, default=None, init=False)
    _user_duration = attr.ib(type=float, default=0.0, init=False)
    _timestamp = attr.ib(
        type=str, default=str(datetime.utcnow().isoformat("T")), init=False
    )
    _tool_inventory = attr.ib(type=Dict[str, Type[Tool]], init=False, default=None)
    _tools = attr.ib(type=Dict[str, Tool], init=False, default=None)

    @property
    def formatters(self) -> List[Formatter]:
        if self._formatters is None:
            self._formatters = self._load_formatters()
        return self._formatters

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

    @property
    def timestamp(self) -> str:
        return self._timestamp

    def elapsed(self) -> float:
        return time.time() - self._start

    def user_duration(self) -> Optional[float]:
        """
        Returns elapsed time in seconds since formatter was opened
        """
        return self._user_duration

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

    def start_user_timer(self) -> None:
        self._user_start = time.perf_counter()

    def stop_user_timer(self) -> None:
        if self._user_start is None:
            return
        self._user_duration += time.perf_counter() - self._user_start

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
            if "run" in tool_config and not tool_config["run"]:
                continue

            ti = inventory.get(tn, None)
            if not ti:
                # TODO: Move to display layer
                echo_error(f"No tool named '{tn}' could be found")
                continue

            tools[tn] = ti(self)

        return tools

    def _load_formatters(self) -> List[Formatter]:
        """
        Returns this project's configured formatter
        """
        if "formatter" not in self.config:
            return [bento.formatter.stylish.Stylish()]
        else:
            FormatterConfig = Dict[str, Any]
            FormatterSpec = Tuple[str, FormatterConfig]

            cfg = self.config["formatter"]

            # Before 0.6, configuration is a simple (unordered) dictionary:
            it: Iterator[FormatterSpec]
            if isinstance(cfg, dict):
                it = iter(cfg.items())
            # After 0.6, configuration is ordered list of dictionaries,
            # Convert to ordered list of tuples.
            else:
                it = (next(iter(f.items())) for f in cfg)

            return [bento.formatter.for_name(f_class, cfg) for f_class, cfg in it]
