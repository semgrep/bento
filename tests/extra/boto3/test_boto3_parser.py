import os
from pathlib import Path

from bento.extra.boto3 import Boto3Parser, Boto3Tool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_parse() -> None:
    with (THIS_PATH / "boto3_violation_simple.json").open() as json_file:
        json = json_file.read()

    result = Boto3Parser(BASE_PATH).parse(json)

    expectation = [
        Violation(
            tool_id="r2c.boto3",
            check_id="hardcoded-access-token",
            path="bad.py",
            line=4,
            column=1,
            message="Hardcoded access token detected. Consider using a config file or environment variables.",
            severity=2,
            syntactic_context="Session(aws_access_key_id='AKIA1235678901234567',",
            filtered=None,
            link="https://checks.bento.dev/en/latest/flake8-boto3/hardcoded-access-token",
        )
    ]

    assert result == expectation


def test_run_no_base_violations(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = Boto3Tool(context_for(tmp_path, Boto3Tool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    assert not violations


def test_run_flask_violations(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/boto3"
    tool = Boto3Tool(context_for(tmp_path, Boto3Tool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    expectation = [
        Violation(
            tool_id="r2c.boto3",
            check_id="hardcoded-access-token",
            path="bad.py",
            line=4,
            column=11,
            message="Hardcoded access token detected. Consider using a config file or environment variables.",
            severity=2,
            syntactic_context="session = Session(aws_access_key_id='AKIA1235678901234567',",
            filtered=None,
            link="https://checks.bento.dev/en/latest/flake8-boto3/hardcoded-access-token",
        )
    ]

    assert violations == expectation
