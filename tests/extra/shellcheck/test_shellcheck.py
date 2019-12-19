import os
from pathlib import Path

from _pytest.tmpdir import tmp_path_factory
from bento.extra.shellcheck import ShellcheckTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests" / "integration" / "shell"
    tool = ShellcheckTool(
        context_for(tmp_path_factory, ShellcheckTool.tool_id(), base_path)
    )
    tool.setup()
    violations = tool.results()
    assert violations == [
        Violation(
            tool_id="r2c.shellcheck",
            check_id="SC2068",
            path="foo.sh",
            line=3,
            column=6,
            message="Double quote array expansions to avoid re-splitting elements.",
            severity=2,
            syntactic_context="echo $@\n",
            filtered=None,
            link="https://github.com/koalaman/shellcheck/wiki/SC2068",
        )
    ]
