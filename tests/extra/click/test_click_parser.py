import os
from pathlib import Path

from bento.extra.click import ClickParser, ClickTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."

EXPECTATIONS = [
    Violation(
        tool_id="r2c.click",
        check_id="option-function-argument-check",
        path="bad_examples.py",
        line=12,
        column=1,
        message="function `bad_option_one` missing parameter `d` for `@click.option`",
        severity=2,
        syntactic_context="@click.command()",
        filtered=None,
        link="",
    ),
    Violation(
        tool_id="r2c.click",
        check_id="names-are-well-formed",
        path="bad_examples.py",
        line=19,
        column=1,
        message="option 'd' should begin with a '-'",
        severity=2,
        syntactic_context="@click.command()",
        filtered=None,
        link="",
    ),
    Violation(
        tool_id="r2c.click",
        check_id="names-are-well-formed",
        line=26,
        path="bad_examples.py",
        column=1,
        message="argument '-a' should not begin with a '-'",
        severity=2,
        syntactic_context="@click.command()",
        filtered=None,
        link="",
    ),
    Violation(
        tool_id="r2c.click",
        check_id="names-are-well-formed",
        path="bad_examples.py",
        line=33,
        column=1,
        message="missing parameter name",
        severity=2,
        syntactic_context="@click.command()",
        filtered=None,
        link="",
    ),
    Violation(
        tool_id="r2c.click",
        check_id="launch-uses-literal",
        path="bad_examples.py",
        line=41,
        column=5,
        message="calls to click.launch() should use literal urls to prevent arbitrary site redirects",
        severity=2,
        syntactic_context="    click.launch(x)",
        filtered=None,
        link="",
    ),
]


def test_parse() -> None:
    with (THIS_PATH / "click_violation_simple.json").open() as json_file:
        json = json_file.read()

    result = ClickParser(BASE_PATH).parse(json)
    assert result == EXPECTATIONS


def test_run_no_base_violations(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = ClickTool(context_for(tmp_path, ClickTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    assert not violations


def test_run_click_violations(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/click"
    tool = ClickTool(context_for(tmp_path, ClickTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()
    assert violations == EXPECTATIONS
