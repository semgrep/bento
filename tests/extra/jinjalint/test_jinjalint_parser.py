import os
from pathlib import Path

from bento.extra.jinjalint import JinjalintTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/simple"
    tool = JinjalintTool(context_for(tmp_path, JinjalintTool.TOOL_ID, base_path))
    tool.setup()
    violations = tool.results()

    expectation = [
        Violation(
            check_id="jinjalint-anchor-missing-noreferrer",
            tool_id=JinjalintTool.TOOL_ID,
            path="jinja-template.html",
            line=11,
            column=8,
            message="Pages opened with 'target=\"_blank\"' allow the new page to access the original's referrer. This can have privacy implications. Include 'rel=\"noreferrer\"' to prevent this.",
            severity=2,
            syntactic_context="",
            link=None,
        ),
        Violation(
            check_id="jinjalint-anchor-missing-noopener",
            tool_id=JinjalintTool.TOOL_ID,
            path="jinja-template.html",
            line=8,
            column=11,
            message="Pages opened with 'target=\"_blank\"' allow the new page to access the original's 'window.opener'. This can have security and performance implications. Include 'rel=\"noopener\"' to prevent this.",
            severity=2,
            syntactic_context="",
            link=None,
        ),
        Violation(
            check_id="jinjalint-form-missing-csrf-protection",
            tool_id=JinjalintTool.TOOL_ID,
            path="jinja-template.html",
            line=7,
            column=8,
            message="Flask apps using 'flask-wtf' require including a CSRF token in the HTML form. This check detects missing CSRF protection in HTML forms in Jinja templates.",
            severity=2,
            syntactic_context="",
            link=None,
        ),
    ]

    assert set(violations) == set(expectation)  # Avoid ordering constraints with set