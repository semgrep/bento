import os
import re
from typing import Callable, Iterable, List, Pattern, Type

from bento.tool import Parser, Tool, ToolContext
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

    @classmethod
    def matches_project(cls, base_path: str) -> bool:
        return True

    def setup(self) -> None:
        pass

    def run(self, files: Iterable[str]) -> str:
        return ",".join(files)


def test_file_path_filter_terminal(
    make_tool_context: Callable[[str], ToolContext]
) -> None:
    tool = ToolFixture(tool_context=make_tool_context(THIS_PATH))
    result = tool.filter_paths(["test_tool.py", "foo.py"])
    expectation = set(["test_tool.py"])

    assert result == expectation


def test_file_path_match(make_tool_context: Callable[[str], ToolContext]) -> None:
    tool = ToolFixture(tool_context=make_tool_context(THIS_PATH))
    result = tool.filter_paths([THIS_PATH])
    expectation = set([THIS_PATH])

    assert result == expectation


def test_file_path_no_match(make_tool_context: Callable[[str], ToolContext]) -> None:
    tool = ToolFixture(tool_context=make_tool_context(THIS_PATH))
    search_path = os.path.join(THIS_PATH, "integration", "simple")
    result = tool.filter_paths([search_path])

    assert not result


def test_tool_run_no_paths(make_tool_context: Callable[[str], ToolContext]) -> None:
    tool = ToolFixture(tool_context=make_tool_context(THIS_PATH))
    result = tool.results()

    assert result == [result_for(THIS_PATH)]


def test_tool_run_file(make_tool_context: Callable[[str], ToolContext]) -> None:
    tool = ToolFixture(tool_context=make_tool_context(THIS_PATH))
    result = tool.results(["test_tool.py"])

    assert result == [result_for("test_tool.py")]


def test_tool_run_ignores(make_tool_context: Callable[[str], ToolContext]) -> None:
    tool = ToolFixture(
        tool_context=make_tool_context(THIS_PATH), config={"ignore": ["test"]}
    )
    result = tool.results()

    assert not result
