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


def test_stylish_formatter() -> None:
    stylish = bento.formatter.for_name("stylish", {})
    output = stylish.dump(VIOLATIONS)
    expectation = [
        "bento/test/integration/init.js",
        f"  0:0  {click.style('error  ', fg='red')} Missing semicolon.            r2c.eslint     semi https://eslint.org/docs/rules/semi",
        f"  0:0  {click.style('warning', fg='yellow')} Unexpected console statement. r2c.eslint     no-console https://eslint.org/docs/rules/no-console",
        "",
    ]

    assert output == expectation


def test_clippy_formatter() -> None:
    clippy = bento.formatter.for_name("clippy", {})
    output = clippy.dump(VIOLATIONS)
    expectation = [
        "\x1b[1m==> Bento Summary\x1b[0m",
        "\x1b[1m\x1b[31merror\x1b[0m: \x1b[1mr2c.eslint.semi https://eslint.org/docs/rules/semi\x1b[0m",
        "   \x1b[34m-->\x1b[0m bento/test/integration/init.js:0:0",
        "    \x1b[34m|\x1b[0m\n \x1b[34m 0\x1b[0m \x1b[34m|\x1b[0m   console.log(3)\n    \x1b[34m|\x1b[0m\n    = \x1b[1mnote:\x1b[0m Missing semicolon.           \n",
        "\x1b[1m\x1b[33mwarning\x1b[0m: \x1b[1mr2c.eslint.no-console https://eslint.org/docs/rules/no-console\x1b[0m",
        "   \x1b[34m-->\x1b[0m bento/test/integration/init.js:0:0",
        "    \x1b[34m|\x1b[0m\n \x1b[34m 0\x1b[0m \x1b[34m|\x1b[0m   console.log(3)\n    \x1b[34m|\x1b[0m\n    = \x1b[1mnote:\x1b[0m Unexpected console statement.\n",
        "",
    ]

    assert output == expectation


def test_json_formatter() -> None:
    json_formatter = bento.formatter.for_name("json", {})
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
