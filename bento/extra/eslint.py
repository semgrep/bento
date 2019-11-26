import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Pattern, Type

import click
import yaml
from semantic_version import Version

from bento.base_context import BaseContext
from bento.extra.js_tool import JsTool, NpmDeps
from bento.parser import Parser
from bento.result import Violation
from bento.tool import JsonR, JsonTool

# Input example:
# [
#   {
#     "filePath":"/Users/nbrahms/dev/echelon-backend/r2c/bento/test/integration/init.js",
#     "messages":[
#       {"ruleId":"no-console","severity":1,"message":"Unexpected console statement.","line":1,"column":1,"nodeType":"MemberExpression","messageId":"unexpected","endLine":1,"endColumn":12},
#       {"ruleId":"semi","severity":2,"message":"Missing semicolon.","line":1,"column":15,"nodeType":"ExpressionStatement","fix":{"range":[14,14],"text":";"}}
#     ],
#     "errorCount":1,
#     "warningCount":1,
#     "fixableErrorCount":1,
#     "fixableWarningCount":0,
#     "source":"console.log(3)\n"
#   }
# ]
#

RC_ENVIRONMENTS = "env"
"""'env' field of .eslintrc.yml"""


class EslintParser(Parser[JsonR]):
    def to_violation(
        self, result: Dict[str, Any], message: Dict[str, Any]
    ) -> Violation:
        path = self.trim_base(result["filePath"])
        startLine = message["line"]
        endLine = message.get("endLine", startLine)
        # todo: remove white-space diffs for non-py?
        source = result["source"][startLine - 1 : endLine]  # line numbers are 1-indexed
        check_id = message.get("ruleId", None)
        if check_id:
            link = f"https://eslint.org/docs/rules/{check_id}"
        else:
            check_id = "error"
            link = ""

        return Violation(
            tool_id=EslintTool.ESLINT_TOOL_ID,
            check_id=check_id,
            path=path,
            line=startLine,
            column=message["column"],
            message=message["message"],
            severity=message["severity"],
            syntactic_context="\n".join(source).strip(),
            link=link,
        )

    def parse(self, tool_output: JsonR) -> List[Violation]:
        violations: List[Violation] = []
        for r in tool_output:
            r["source"] = r.get("source", "").split("\n")
            violations += [self.to_violation(r, m) for m in r["messages"]]
        return violations


class EslintTool(JsTool, JsonTool):
    ESLINT_TOOL_ID = "r2c.eslint"  # to-do: versioning?
    CONFIG_FILE_NAME = ".eslintrc.yml"
    PROJECT_NAME = "node-js"

    # Packages we always need no matter what.
    ALWAYS_NEEDED = {
        "eslint": Version("6.1.0"),
        "eslint-config-airbnb": Version("18.0.1"),
        "eslint-plugin-import": Version("2.18.2"),
        "eslint-plugin-jsx-a11y": Version("6.2.3"),
        "eslint-plugin-react": Version("7.14.3"),
        "eslint-plugin-react-hooks": Version("1.7.0"),
    }
    MIN_ESLINT_PLUGIN_REACT_VERSION = Version("7.14.3")
    TYPESCRIPT_PACKAGES = {
        "@typescript-eslint/parser": Version("2.3.3"),
        "@typescript-eslint/eslint-plugin": Version("2.3.3"),
    }

    # Never fire on 'window', etc.
    ALWAYS_INCLUDE_GLOBALS = ["browser", "commonjs", "es6", "node"]

    # Remaining environments are determined by inspecting package.json
    POSSIBLE_GLOBALS = [
        "applescript",
        "atomtest",
        "embertest",
        "greasemonkey",
        "jasmine",
        "jest",
        "jquery",
        "mango",
        "meteor",
        "mocha",
        "nashorn",
        "phantomjs",
        "prototypejs",
        "protractor",
        "qunit",
        "serviceworker",
        "shelljs",
        "webextensions",
    ]

    @property
    def parser_type(self) -> Type[Parser]:
        return EslintParser

    @classmethod
    def tool_id(self) -> str:
        return EslintTool.ESLINT_TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Identifies and reports on patterns in JavaScript and TypeScript"

    @property
    def project_name(self) -> str:
        deps = self._dependencies()
        all_used = [g for g in self.POSSIBLE_GLOBALS if g in deps]
        if self.__uses_typescript(deps):
            all_used.append("TypeScript")
        if self.__uses_react(deps):
            all_used.append("react")

        if all_used:
            fws = ", ".join(sorted(all_used))
            return f"{EslintTool.PROJECT_NAME} (with {fws})"
        return EslintTool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r".*\.(?:js|jsx|ts|tsx)\b")

    @property
    def eslintrc_path(self) -> Path:
        return self.base_path / EslintTool.CONFIG_FILE_NAME

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return (context.base_path / "package.json").exists()

    def __uses_typescript(self, deps: NpmDeps) -> bool:
        return (
            "typescript" in deps
        )  # ts dependency shouldn't be in main deps, but, if it is, ok

    def __uses_react(self, deps: NpmDeps) -> bool:
        return "react" in deps.main  # react dependency must be in main deps

    def __load_default_rc(self) -> Dict[str, Any]:
        with self.eslintrc_path.open() as stream:
            return yaml.safe_load(stream)

    def __copy_eslintrc(self, identifier: str) -> None:
        click.secho(f"Using {identifier} .eslintrc configuration", err=True)
        shutil.copy(
            os.path.join(
                os.path.dirname(__file__), f"eslint/.eslintrc-{identifier}.yml"
            ),
            self.eslintrc_path,
        )

    def __add_globals(self, deps: NpmDeps) -> None:
        """Adds global environments to eslintrc"""
        node_globals = [
            g for g in self.POSSIBLE_GLOBALS if g in deps
        ] + self.ALWAYS_INCLUDE_GLOBALS
        env_dict = dict((g, True) for g in node_globals)

        with self.eslintrc_path.open() as stream:
            rc = yaml.safe_load(stream)
        rc[RC_ENVIRONMENTS] = env_dict
        with self.eslintrc_path.open("w") as stream:
            yaml.safe_dump(rc, stream)

    def setup(self) -> None:
        needed_packages = self.ALWAYS_NEEDED.copy()
        deps = self._dependencies()
        project_has_typescript = self.__uses_typescript(deps)
        project_has_react = self.__uses_react(deps)
        if project_has_react:
            needed_packages[
                "eslint-plugin-react"
            ] = EslintTool.MIN_ESLINT_PLUGIN_REACT_VERSION
        if project_has_typescript:
            needed_packages.update(EslintTool.TYPESCRIPT_PACKAGES)

        self._ensure_packages(needed_packages)
        self._ensure_node_version()

        # install .eslintrc.yml if necessary
        if not self.eslintrc_path.exists():
            click.echo(f"Installing {EslintTool.CONFIG_FILE_NAME}...", err=True)

            if project_has_react and project_has_typescript:
                self.__copy_eslintrc("react-and-typescript")
            elif project_has_react:
                self.__copy_eslintrc("react")
            elif project_has_typescript:
                self.__copy_eslintrc("typescript")
            else:
                self.__copy_eslintrc("default")

            self.__add_globals(deps)

    @staticmethod
    def raise_failure(cmd: List[str], result: subprocess.CompletedProcess) -> None:
        # Tool returned fialure, or did not return json
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )

    def run(self, files: Iterable[str]) -> JsonR:
        ignores = [
            arg
            for p in self.context.file_ignores.patterns
            for arg in ["--ignore-pattern", p]
        ]
        disables = [
            arg
            for d in self.config.get("ignore", [])
            for arg in ["--rule", f"{d}: off"]
        ]
        cmd = (
            [
                "./node_modules/eslint/bin/eslint.js",
                "--no-eslintrc",
                "-c",
                EslintTool.CONFIG_FILE_NAME,
                "-f",
                "json",
                "--ext",
                "js,jsx,ts,tsx",
            ]
            + ignores
            + disables
        )
        for f in files:
            cmd.append(f)
        result = self.execute(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"TIMING": "1", **os.environ},
            check=False,
        )
        logging.debug(f"{self.tool_id()}: stderr:\n" + result.stderr[0:4000])
        logging.debug(f"{self.tool_id()}: stdout:\n" + result.stdout[0:4000])

        # Return codes:
        # 0 = no violations, 1 = violations, 2+ = tool failure
        if result.returncode > 1:
            self.raise_failure(cmd, result)

        try:
            # TODO: this double-parses, which we can avoid in the future by having type-parameterized parsers
            lines = result.stdout.split("\n")
            data = lines[0]
            timing = "\n".join(lines[1:])
            logging.debug(f"r2c.eslint: TIMING:\n{timing}")
            return json.loads(data.strip())
        except Exception as ex:
            logging.error("Could not parse json output of eslint tool", ex)
            self.raise_failure(cmd, result)
            return []  # Unreachable, but mypy is poor
