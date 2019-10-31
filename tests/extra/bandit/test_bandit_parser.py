import os
from pathlib import Path

from _pytest.tmpdir import tmp_path_factory
from bento.extra.bandit import BanditTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = BanditTool(context_for(tmp_path_factory, BanditTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    expectation = [
        Violation(
            check_id="error",
            tool_id=BanditTool.TOOL_ID,
            path="foo.py",
            line=0,
            column=0,
            message="syntax error while parsing AST from file",
            severity=4,
            syntactic_context="",
            link=None,
        ),
        Violation(
            check_id="B404",
            tool_id=BanditTool.TOOL_ID,
            path="bar.py",
            line=1,
            column=0,
            message="Consider possible security implications associated with subprocess module.",
            severity=1,
            syntactic_context='import subprocess\ndef do_it(cmd: str) -> None:\nsubprocess.run(f"bash -c {cmd}", shell=True)',
            link="https://bandit.readthedocs.io/en/latest/blacklists/blacklist_imports.html#b404-import-subprocess",
        ),
        Violation(
            check_id="B602",
            tool_id=BanditTool.TOOL_ID,
            path="bar.py",
            line=4,
            column=0,
            message="subprocess call with shell=True identified, security issue.",
            severity=3,
            syntactic_context='def do_it(cmd: str) -> None:\nsubprocess.run(f"bash -c {cmd}", shell=True)',
            link="https://bandit.readthedocs.io/en/latest/plugins/b602_subprocess_popen_with_shell_equals_true.html",
        ),
    ]

    assert violations == expectation
