import os
from pathlib import Path

from bento.extra.sgrep import SGrepTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run(tmp_path: Path) -> None:
    base_path = BASE_PATH / "tests/integration/sgrep"
    tool = SGrepTool(context_for(tmp_path, SGrepTool.tool_id(), base_path))
    tool.setup()
    violations = tool.results()
    print(violations)
    expectation = [
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_DEBUG",
            path="flask_configs.py",
            line=33,
            column=1,
            message=" Hardcoded variable `DEBUG` detected. Set this by using FLASK_DEBUG environment variable",
            severity=2,
            syntactic_context='app.config["DEBUG"] = False',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_DEBUG",
            path="flask_configs.py",
            line=31,
            column=1,
            message=" Hardcoded variable `DEBUG` detected. Set this by using FLASK_DEBUG environment variable",
            severity=2,
            syntactic_context='app.config["DEBUG"] = True',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_ENV",
            path="flask_configs.py",
            line=27,
            column=1,
            message=" Hardcoded variable `ENV` detected. Set this by using FLASK_ENV environment variable",
            severity=2,
            syntactic_context='app.config["ENV"] = "production"',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_ENV",
            path="flask_configs.py",
            line=25,
            column=1,
            message=" Hardcoded variable `ENV` detected. Set this by using FLASK_ENV environment variable",
            severity=2,
            syntactic_context='app.config["ENV"] = "development"',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_SECRET_KEY",
            path="flask_configs.py",
            line=21,
            column=1,
            message=" Hardcoded variable `SECRET_KEY` detected. Use environment variables or config files instead",
            severity=2,
            syntactic_context='app.config["SECRET_KEY"] = b\'_5#y2L"F4Q8z\\n\\xec]/\'',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_SECRET_KEY",
            path="flask_configs.py",
            line=19,
            column=1,
            message=" Hardcoded variable `SECRET_KEY` detected. Use environment variables or config files instead",
            severity=2,
            syntactic_context='app.config.update(SECRET_KEY="aaaa")',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_TESTING",
            path="flask_configs.py",
            line=15,
            column=1,
            message=" Hardcoded variable `TESTING` detected. Use environment variables or config files instead",
            severity=2,
            syntactic_context="app.config.update(TESTING=True)",
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_TESTING",
            path="flask_configs.py",
            line=13,
            column=1,
            message=" Hardcoded variable `TESTING` detected. Use environment variables or config files instead",
            severity=2,
            syntactic_context='app.config["TESTING"] = False',
            filtered=None,
            link=None,
        ),
        Violation(
            tool_id="sgrep",
            check_id="avoid_hardcoded_config_TESTING",
            path="flask_configs.py",
            line=11,
            column=1,
            message=" Hardcoded variable `TESTING` detected. Use environment variables or config files instead",
            severity=2,
            syntactic_context='app.config["TESTING"] = True',
            filtered=None,
            link=None,
        ),
    ]

    assert violations == expectation
