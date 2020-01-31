import os
from pathlib import Path

from bento.extra.checked_return import CheckedReturnTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/checked_return"
    tool = CheckedReturnTool(
        context_for(tmp_path, CheckedReturnTool.tool_id(), base_path)
    )
    tool.setup()
    violations = tool.results([base_path / "checkedreturn.js"])
    expectation = [
        Violation(
            tool_id="r2c.checked_return",
            check_id="checked_return",
            path="checkedreturn.js",
            line=25,
            column=3,
            message="./checkedreturn.js:25:2: error unchecked return for must_be_used (used = 11, ignored = 1)",
            severity=2,
            syntactic_context="  must_be_used(); //maybe a bug, but not counted for now, maybe used for its throwing effect",
        )
    ]

    assert violations == expectation
