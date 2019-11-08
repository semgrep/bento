import os
from pathlib import Path

from _pytest.tmpdir import tmp_path_factory
from bento.extra.click import ClickParser, ClickTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."

EXPECTATIONS = [
    Violation(
        tool_id="r2c.click",
        check_id="CLC100:",
        path="cli.py",
        line=3,
        column=1,
        message="function `cli` missing parameter `version` for `@click.option`",
        severity=2,
        syntactic_context='@click.option("--version")',
        filtered=None,
        link="",
    ),
    Violation(
        tool_id="r2c.click",
        check_id="CLC001",
        path="cli.py",
        line=3,
        column=2,
        message="@click.option should have `help` text",
        severity=2,
        syntactic_context='@click.option("--version")',
        filtered=None,
        link="",
    ),
]


def test_parse() -> None:
    with (THIS_PATH / "click_violation_simple.json").open() as json_file:
        json = json_file.read()

    result = ClickParser(BASE_PATH).parse(json)

    assert result == EXPECTATIONS


def test_run_no_base_violations(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = ClickTool(context_for(tmp_path_factory, ClickTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    assert not violations


def test_run_Click_violations(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/click"
    tool = ClickTool(context_for(tmp_path_factory, ClickTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    assert violations == EXPECTATIONS
