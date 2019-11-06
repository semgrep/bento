import textwrap

import bento.result as result
from bento.violation import Violation

VIOLATIONS = [
    Violation(
        tool_id="r2c.eslint",
        check_id="no-console",
        path="bento/test/integration/init.js",
        line=0,
        column=0,
        severity=1,
        message="Unexpected console statement.",
        syntactic_context="console.log(3)",
    ),
    Violation(
        tool_id="r2c.eslint",
        check_id="semi",
        path="bento/test/integration/init.js",
        line=0,
        column=0,
        message="Missing semicolon.",
        severity=2,
        syntactic_context="console.log(3)",
    ),
]

YML_TEXT = textwrap.dedent(
    """
    r2c_eslint:
      violations:
        ab901b8d5807dcf6074c35f9aa053ec2:
          check_id: no-console
          message: Unexpected console statement.
          path: bento/test/integration/init.js
          severity: 1
          syntactic_context: console.log(3)
          tool_id: r2c.eslint
        c9a8cb6fa4b224d27c0719d10c9de6a5:
          check_id: semi
          message: Missing semicolon.
          path: bento/test/integration/init.js
          severity: 2
          syntactic_context: console.log(3)
          tool_id: r2c.eslint
    """
)[1:]


def test_tool_yml() -> None:
    generated = result.tool_results_to_yml("r2c_eslint", VIOLATIONS)

    assert generated == YML_TEXT


def test_yml_to_violation_hashes() -> None:

    hashes_by_tool = result.yml_to_violation_hashes(YML_TEXT)

    expectation = {
        "r2c_eslint": {
            "ab901b8d5807dcf6074c35f9aa053ec2",
            "c9a8cb6fa4b224d27c0719d10c9de6a5",
        }
    }

    assert hashes_by_tool == expectation


def test_filter_results() -> None:
    baseline = {"r2c_eslint": {"ab901b8d5807dcf6074c35f9aa053ec2"}}

    filtered = result.filtered("r2c_eslint", VIOLATIONS, baseline)
    assert filtered[0].filtered
    assert not filtered[1].filtered
