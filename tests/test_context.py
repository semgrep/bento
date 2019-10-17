import os
from typing import Any, Dict

import bento.context

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, ".."))


def test_tool_from_config_found() -> None:
    """Validates that existing tools are parsed from the config file"""
    config: Dict[str, Any] = {"tools": {"r2c.eslint": {"ignore": []}}}
    context = bento.context.Context(config=config)
    tools = context.tools
    assert len(tools) == 1
    assert tools.keys() == {"r2c.eslint"}


def test_tool_from_config_missing() -> None:
    """Validates that non-existant tools are silently ignored in the config file"""
    config: Dict[str, Any] = {"tools": {"r2c.not_a_thing": {"ignore": []}}}
    context = bento.context.Context(config=config)
    assert len(context.tools) == 0
