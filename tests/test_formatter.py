import json

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
    output = stylish.dump(VIOLATIONS)
    expectation = [
        "bento/test/integration/init.js",
        f"  0:0  {click.style('warning', fg='yellow')} Unexpected console statement. r2c.eslint     no-console https://eslint.org/docs/rules/no-console",
        f"  0:0  {click.style('error  ', fg='red')} Missing semicolon.            r2c.eslint     semi https://eslint.org/docs/rules/semi",
        "",
    ]

    assert output == expectation


def test_json_formatter():
    json_formatter = bento.formatter.Json()
    json_formatter.config = {}
    output = json.loads(next(iter(json_formatter.dump(VIOLATIONS))))
    assert output == [
        {
            "tool_id": "r2c.eslint",
            "check_id": "no-console",
            "line": 0,
            "column": 0,
            "severity": 1,
            "message": "Unexpected console statement.",
            "path": "bento/test/integration/init.js",
        },
        {
            "tool_id": "r2c.eslint",
            "check_id": "semi",
            "path": "bento/test/integration/init.js",
            "line": 0,
            "column": 0,
            "severity": 2,
            "message": "Missing semicolon.",
        },
    ]
