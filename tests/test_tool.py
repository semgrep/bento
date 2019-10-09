import os
import re
from typing import Pattern

from bento.tool import Any, Dict, Iterable, List, Parser, Tool, Type
from bento.violation import Violation

THIS_PATH = os.path.dirname(__file__)


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


class ParserFixture(Parser):
    def parse(self, input: str) -> List[Violation]:
        return [result_for(f) for f in input.split(",")]


class ToolFixture(Tool):
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

    def matches_project(self) -> bool:
        return True

    def setup(self, config: Dict[str, Any]) -> None:
        pass

    def run(self, config: Dict[str, Any], files: Iterable[str]) -> str:
        return ",".join(files)


def test_file_path_filter_terminal() -> None:
    tool = ToolFixture()
    result = tool.filter_paths({}, ["test_tool.py", "foo.py"])
    expectation = set(["test_tool.py"])

    assert result == expectation


def test_file_path_match() -> None:
    tool = ToolFixture()
    result = tool.filter_paths({}, [THIS_PATH])
    expectation = set([THIS_PATH])

    assert result == expectation


def test_file_path_no_match() -> None:
    tool = ToolFixture()
    search_path = os.path.join(THIS_PATH, "integration", "simple")
    result = tool.filter_paths({}, [search_path])

    assert not result


def test_tool_run_no_paths() -> None:
    tool = ToolFixture()
    tool.base_path = THIS_PATH
    result = tool.results({})

    assert result == [result_for(THIS_PATH)]


def test_tool_run_file() -> None:
    tool = ToolFixture()
    tool.base_path = THIS_PATH
    result = tool.results({}, ["test_tool.py"])

    assert result == [result_for("test_tool.py")]


def test_tool_run_ignores() -> None:
    tool = ToolFixture()
    tool.base_path = THIS_PATH
    result = tool.results({"ignore": ["test"]})

    assert not result
