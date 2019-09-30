import click

import bento.formatter
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
        link="https://eslint.org/docs/rules/no-console",
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
        link="https://eslint.org/docs/rules/semi",
    ),
]


def test_stylish_formatter():
    stylish = bento.formatter.Stylish()
    stylish.config = {}
    output = stylish.to_lines(VIOLATIONS)
    expectation = [
        "bento/test/integration/init.js",
        f"  0:0  {click.style('warning', fg='yellow')} Unexpected console statement.                      r2c.eslint     https://eslint.org/docs/rules/no-console",
        f"  0:0  {click.style('error  ', fg='red')} Missing semicolon.                                 r2c.eslint     https://eslint.org/docs/rules/semi",
        "",
    ]

    assert output == expectation
