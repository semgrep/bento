import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Type

from _pytest.tmpdir import tmp_path_factory
from bento.base_context import BaseContext
from bento.tool import Parser, Tool
from bento.violation import Violation

THIS_PATH = Path(os.path.dirname(__file__))


def result_for(path: str) -> Violation:
    return Violation(
        tool_id="test",
        check_id="test",
        path=path,
        line=0,
        column=0,
        message="test",
        severity=2,
        syntactic_context="test",
    )


def context_for(
    tmp_path_factory: tmp_path_factory,
    tool_id: str,
    base_path: Path = THIS_PATH,
    config: Optional[Dict[str, Any]] = None,
) -> BaseContext:
    return BaseContext(
        base_path=base_path,
        config={"tools": {tool_id: config or {}}},
        cache_path=tmp_path_factory.mktemp("cache-dir-"),
        resource_path=tmp_path_factory.mktemp("resource-dir-"),
    )


class ParserFixture(Parser):
    def parse(self, tool_output: str) -> List[Violation]:
        return [result_for(f) for f in tool_output.split(",")]


class ToolFixture(Tool):
    def __init__(
        self,
        tmp_path_factory: Any,
        base_path: Path = THIS_PATH,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(context_for(tmp_path_factory, "test", base_path, config))

    @property
    def parser_type(self) -> Type[Parser]:
        return ParserFixture

    @classmethod
    def tool_id(self) -> str:
        return "test"

    @property
    def project_name(self) -> str:
        return "Test"

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r"\btest_tool\.py\b")

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return True

    def setup(self) -> None:
        pass

    def run(self, files: Iterable[str]) -> str:
        return ",".join(files)


def test_file_path_filter_terminal(tmp_path_factory: tmp_path_factory) -> None:
    tool = ToolFixture(tmp_path_factory)
    result = tool.filter_paths(["test_tool.py", "foo.py"])
    expectation = {"test_tool.py"}

    assert result == expectation


def test_file_path_match(tmp_path_factory: tmp_path_factory) -> None:
    tool = ToolFixture(tmp_path_factory)
    result = tool.filter_paths([str(THIS_PATH)])
    expectation = {str(THIS_PATH)}

    assert result == expectation


def test_file_path_no_match(tmp_path_factory: tmp_path_factory) -> None:
    tool = ToolFixture(tmp_path_factory)
    search_path = THIS_PATH / "integration" / "simple"
    result = tool.filter_paths([str(search_path)])

    assert not result


def test_tool_run_no_paths(tmp_path_factory: tmp_path_factory) -> None:
    tool = ToolFixture(tmp_path_factory)
    result = tool.results()

    assert result == [result_for(str(THIS_PATH))]


def test_tool_run_file(tmp_path_factory: tmp_path_factory) -> None:
    tool = ToolFixture(tmp_path_factory)
    result = tool.results(["test_tool.py"])

    assert result == [result_for("test_tool.py")]


def test_tool_run_ignores(tmp_path_factory: tmp_path_factory) -> None:
    tool = ToolFixture(tmp_path_factory, config={"ignore": ["test"]})
    result = tool.results()

    assert not result
