import os
import subprocess

from bento.extra.eslint import EslintParser, EslintTool
from bento.violation import Violation

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../../.."))


def test_parse():
    with open(os.path.join(THIS_PATH, "eslint_violation_simple.json")) as json_file:
        json = json_file.read()

    result = EslintParser(BASE_PATH).parse(json)

    expectation = [
        Violation(
            tool_id="r2c.eslint",
            check_id="no-console",
            path="tests/integration/simple/init.js",
            line=0,
            column=0,
            message="Unexpected console statement.",
            severity=1,
            syntactic_context="console.log(3)",
        ),
        Violation(
            tool_id="r2c.eslint",
            check_id="semi",
            path="tests/integration/simple/init.js",
            line=0,
            column=0,
            message="Missing semicolon.",
            severity=2,
            syntactic_context="console.log(3)",
        ),
    ]

    assert result == expectation


def test_line_move():
    parser = EslintParser(BASE_PATH)

    with open(
        os.path.join(THIS_PATH, "eslint_violation_move_before.json")
    ) as json_file:
        before = parser.parse(json_file.read())
    with open(os.path.join(THIS_PATH, "eslint_violation_move_after.json")) as json_file:
        after = parser.parse(json_file.read())

    assert before == after
    assert [b.syntactic_identifier_str() for b in before] == [
        a.syntactic_identifier_str() for a in after
    ]


def test_run():
    tool = EslintTool()
    tool.base_path = os.path.abspath(
        os.path.join(BASE_PATH, "tests/integration/simple")
    )
    tool.setup({})
    try:
        violations = tool.results({})
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        raise e

    expectation = [
        Violation(
            tool_id="r2c.eslint",
            check_id="no-console",
            path="init.js",
            line=0,
            column=0,
            message="Unexpected console statement.",
            severity=1,
            syntactic_context="console.log(3)",
        ),
        Violation(
            tool_id="r2c.eslint",
            check_id="semi",
            path="init.js",
            line=0,
            column=0,
            message="Missing semicolon.",
            severity=2,
            syntactic_context="console.log(3)",
        ),
    ]

    assert violations == expectation


def test_file_match():
    f = EslintTool().file_name_filter

    assert f.match("js") is None
    assert f.match("foo.js") is not None
    assert f.match("foo.jsx") is not None
    assert f.match("foo.ts") is not None
    assert f.match("foo.tsx") is not None
    assert f.match("foo.jsa") is None


def test_missing_source():
    with open(
        os.path.join(THIS_PATH, "eslint_violation_missing_source.json")
    ) as json_file:
        json = json_file.read()

    result = EslintParser(BASE_PATH).parse(json)

    expectation = [
        Violation(
            tool_id="r2c.eslint",
            check_id="no-console",
            path="tests/integration/simple/init.js",
            line=0,
            column=0,
            message="Unexpected console statement.",
            severity=1,
            syntactic_context="",
        )
    ]

    assert result == expectation
