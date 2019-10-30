import os
from typing import Callable

from bento.extra.flake8 import Flake8Parser, Flake8Tool
from bento.tool import ToolContext
from bento.violation import Violation

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../../.."))


def test_parse(make_tool_context: Callable[[str], ToolContext]) -> None:
    with open(os.path.join(THIS_PATH, "flake8_violation_simple.json")) as json_file:
        json = json_file.read()

    result = Flake8Parser(BASE_PATH).parse(json)

    expectation = [
        Violation(
            tool_id="r2c.flake8",
            check_id="E124",
            path="foo.py",
            line=2,
            column=0,
            message="closing bracket does not match visual indentation",
            severity=2,
            syntactic_context="        )",
        )
    ]

    assert result == expectation


def test_run(make_tool_context: Callable[[str], ToolContext]) -> None:
    base_path = os.path.abspath(os.path.join(BASE_PATH, "tests/integration/simple"))
    tool = Flake8Tool(make_tool_context(base_path))
    tool.setup()
    violations = tool.results()

    expectation = [
        Violation(
            tool_id="r2c.flake8",
            check_id="E124",
            path="foo.py",
            line=2,
            column=0,
            message="closing bracket does not match visual indentation",
            severity=2,
            syntactic_context="        )",
        ),
        Violation(
            tool_id="r2c.flake8",
            check_id="E999",
            path="foo.py",
            line=5,
            column=0,
            message="SyntaxError: invalid syntax",
            severity=2,
            syntactic_context="def broken(x)",
        ),
        Violation(
            tool_id="r2c.flake8",
            check_id="E113",
            path="foo.py",
            line=6,
            column=0,
            message="unexpected indentation",
            severity=2,
            syntactic_context="    return x",
        ),
    ]

    assert violations == expectation


def test_file_match(make_tool_context: Callable[[str], ToolContext]) -> None:
    f = Flake8Tool(make_tool_context(BASE_PATH)).file_name_filter

    assert f.match("py") is None
    assert f.match("foo.py") is not None
    assert f.match("foo.pyi") is None
