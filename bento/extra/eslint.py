import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Pattern, Type

from semantic_version import Version

from bento.extra.js_tool import JsTool
from bento.parser import Parser
from bento.result import Violation
from bento.tool import Tool

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


class EslintParser(Parser):
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
            syntactic_context="\n".join(source),
            link=link,
        )

    def parse(self, input: str) -> List[Violation]:
        violations: List[Violation] = []
        for r in json.loads(input):
            r["source"] = r.get("source", "").split("\n")
            violations += [self.to_violation(r, m) for m in r["messages"]]
        return violations


class EslintTool(JsTool, Tool):
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

    @property
    def parser_type(self) -> Type[Parser]:
        return EslintParser

    @classmethod
    def tool_id(self) -> str:
        return EslintTool.ESLINT_TOOL_ID

    @property
    def project_name(self) -> str:
        return EslintTool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r".*\.(?:js|jsx|ts|tsx)\b")

    def matches_project(self) -> bool:
        return os.path.exists(os.path.join(self.base_path, "package.json"))

    def __copy_eslintrc(self, identifier: str) -> None:
        print(f"Using {identifier} .eslintrc configuration")
        shutil.copy(
            os.path.join(
                os.path.dirname(__file__), f"eslint/.eslintrc-{identifier}.yml"
            ),
            os.path.join(self.base_path, EslintTool.CONFIG_FILE_NAME),
        )

    def setup(self, config: Dict[str, Any]) -> None:
        needed_packages = self.ALWAYS_NEEDED.copy()
        project_has_react = self._installed_version("react") is not None
        if project_has_react:
            needed_packages[
                "eslint-plugin-react"
            ] = EslintTool.MIN_ESLINT_PLUGIN_REACT_VERSION
        self._ensure_packages(needed_packages)

        # install .eslintrc.yml
        if not os.path.exists(
            os.path.join(self.base_path, EslintTool.CONFIG_FILE_NAME)
        ):
            print(f"Installing {EslintTool.CONFIG_FILE_NAME}...")

            if project_has_react is not None:
                self.__copy_eslintrc("react")
            else:
                self.__copy_eslintrc("default")

    def run(self, config: Dict[str, Any], files: Iterable[str]) -> str:
        cmd = [
            "./node_modules/eslint/bin/eslint.js",
            "--no-eslintrc",
            "-c",
            EslintTool.CONFIG_FILE_NAME,
            "-f",
            "json",
        ]
        for f in files:
            cmd.append(f)
        result = self.exec(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Return codes:
        # 0 = no violations, 1 = violations, 2+ = tool failure
        if result.returncode > 1:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
        return result.stdout.rstrip()
