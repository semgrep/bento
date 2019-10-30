import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable

import pytest
from bento.run_cache import RunCache
from bento.tool import ToolContext


@pytest.fixture  # type: ignore
def run_cache() -> Iterable[RunCache]:
    """Sets up a RunCache in a temporary directory.

    The temporary directory is *not* the same as pytest's tmp_dir. If you need
    it, you can look at the cache_dir property.
    """
    with tempfile.TemporaryDirectory() as d:
        yield RunCache(Path(d))


@pytest.fixture  # type: ignore
def make_tool_context(tmp_path_factory: Any) -> Callable[[str], ToolContext]:
    """Sets up a context pointing to a nonexistent base_path.

    If a tool needs to set the base_path, it can do so.
    """

    def _make(base_path: str) -> ToolContext:
        return ToolContext(
            base_path=base_path,
            cache_dir=tmp_path_factory.mktemp("cache-dir-"),
            resource_dir=tmp_path_factory.mktemp("resource-dir-"),
        )

    return _make
