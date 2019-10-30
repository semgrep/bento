import os
from typing import Callable

from bento.extra.pyre import PyreTool
from bento.tool import ToolContext
from bento.violation import Violation

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../../.."))


def test_run(make_tool_context: Callable[[str], ToolContext]) -> None:
    base_path = os.path.abspath(os.path.join(BASE_PATH, "tests/integration/py-only"))
    tool = PyreTool(tool_context=make_tool_context(base_path))
    tool.setup()
    violations = tool.results()

    expectation = [
        Violation(
            tool_id="r2c.pyre",
            check_id="6",
            path="bar.py",
            line=10,
            column=13,
            message="Incompatible parameter type [6]: Expected `int` for 1st anonymous parameter to call `int.__radd__` but got `str`.",
            severity=2,
            syntactic_context="    x: int = cmd + 5 + os.getenv('doesnotexist')\n",
            link="https://pyre-check.org/docs/error-types.html",
        ),
        Violation(
            tool_id="r2c.pyre",
            check_id="6",
            path="bar.py",
            line=10,
            column=23,
            message="Incompatible parameter type [6]: Expected `int` for 1st anonymous parameter to call `int.__add__` but got `typing.Optional[str]`.",
            severity=2,
            syntactic_context="    x: int = cmd + 5 + os.getenv('doesnotexist')\n",
            link="https://pyre-check.org/docs/error-types.html",
        ),
        Violation(
            tool_id="r2c.pyre",
            check_id="7",
            path="bar.py",
            line=11,
            column=4,
            message="Incompatible return type [7]: Expected `str` but got `None`.",
            severity=2,
            syntactic_context="    return None\n",
            link="https://pyre-check.org/docs/error-types.html",
        ),
    ]

    assert set(violations) == set(expectation)


def test_file_match(make_tool_context: Callable[[str], ToolContext]) -> None:
    f = PyreTool(tool_context=make_tool_context(BASE_PATH)).file_name_filter

    assert f.match("py") is None
    assert f.match("foo.py") is not None
    assert f.match("foo.pyi") is None
