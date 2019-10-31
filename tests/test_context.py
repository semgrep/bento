from pathlib import Path
from typing import Any, Dict

import bento.context
from _pytest.monkeypatch import MonkeyPatch

THIS_PATH = Path(__file__).parent
BASE_PATH = THIS_PATH / ".."


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


def test_loads_ignores(monkeypatch: MonkeyPatch) -> None:
    context = bento.context.Context(base_path=(Path(BASE_PATH) / "bento" / "configs"))
    expected = {
        "*.min.js",
        "*.egg-info/",
        ".bento/",
        ".eggs/",
        ".git/",
        ".mypy_cache/",
        "__pycache__/",
        "build/",
        "develop-eggs/",
        "dist/",
        "eggs/",
        "lib/",
        "lib64/",
        "node_modules/",
        "packages/",
        "parts/",
        "pip-wheel-metadata/",
        "sdist/",
        "share/python-wheels/",
        "var/",
        "wheels/",
    }
    assert context.file_ignores.patterns == expected
