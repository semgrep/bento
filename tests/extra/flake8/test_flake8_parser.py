import os
from pathlib import Path

from _pytest.tmpdir import tmp_path_factory
from bento.extra.flake8 import Flake8Parser, Flake8Tool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_parse() -> None:
    with (THIS_PATH / "flake8_violation_simple.json").open() as json_file:
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


def test_run(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = Flake8Tool(context_for(tmp_path_factory, Flake8Tool.TOOL_ID, base_path))
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


def test_file_match(tmp_path_factory: tmp_path_factory) -> None:
    f = Flake8Tool(context_for(tmp_path_factory, Flake8Tool.TOOL_ID)).file_name_filter

    assert f.match("py") is None
    assert f.match("foo.py") is not None
    assert f.match("foo.pyi") is None
