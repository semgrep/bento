import os
from pathlib import Path

from _pytest.tmpdir import tmp_path_factory
from bento.extra.requests import RequestsTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run_no_base_violations(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = RequestsTool(context_for(tmp_path_factory, RequestsTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    assert not violations


def test_run_flask_violations(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/requests"
    tool = RequestsTool(context_for(tmp_path_factory, RequestsTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    expectation = [
        Violation(
            tool_id="r2c.requests",
            check_id="no-auth-over-http",
            path="bad.py",
            line=2,
            column=5,
            message="auth is possibly used over http://, which could expose credentials. possible_urls: ['http://MYURL.com']",
            severity=2,
            syntactic_context="r = requests.get('http://MYURL.com', auth=('user', 'pass'))",
            filtered=None,
            link="https://checks.bento.dev/en/latest/flake8-requests/r2c-requests-no-auth-over-http",
        )
    ]

    assert violations == expectation
