import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Pattern, Type

from semantic_version import Version

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
            r["source"] = r["source"].split("\n")
            violations += [self.to_violation(r, m) for m in r["messages"]]
        return violations


class EslintTool(Tool):
    ESLINT_TOOL_ID = "r2c.eslint"  # to-do: versioning?
    CONFIG_FILE_NAME = ".eslintrc.yml"
    MIN_ESLINT_VERSION = Version("6.1.0")
    PROJECT_NAME = "node-js"

    # TODO: semantic versioning compatibility
    MIN_ESLINT_VERSION = Version("6.1.0")
    MIN_AIRBNB_VERSION = Version("18.0.1")
    MIN_PEERDEPS_VERSION = Version("1.10.2")
    MIN_REACT_VERSION = Version("7.14.3")

    installed_versions: Dict[str, Version] = {}

    @property
    def parser_type(self) -> Type[Parser]:
        return EslintParser

    @property
    def tool_id(self) -> str:
        return EslintTool.ESLINT_TOOL_ID

    @property
    def project_name(self) -> str:
        return EslintTool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r".*\.(?:js|jsx|ts|tsx)\b")

    def __list_installed_versions(self) -> None:
        npm_query = self.exec(
            ["npm", "list", "--depth=0"], capture_output=True
        ).stdout.split("\n")[1:]
        regex = re.compile(r"([^\s]+)@([\d\.]+)")
        for pkg_info in npm_query:
            results = regex.search(pkg_info)
            if results:
                pkg, ver = results.groups()
                self.installed_versions[pkg] = Version(ver)

    def __copy_eslintrc(self, identifier: str) -> None:
        print(f"Using {identifier} .eslintrc configuration")
        shutil.copy(
            os.path.join(
                os.path.dirname(__file__), f"eslint/.eslintrc-{identifier}.yml"
            ),
            os.path.join(self.base_path, EslintTool.CONFIG_FILE_NAME),
        )

    def __npm_install(self, package: str, min_version: Version) -> bool:
        package_version = self.installed_versions.get(package, None)
        needs_update = True
        if package_version is not None:
            # TODO: Move to debug logging
            # print(f"Current {package} version is {package_version}")
            if package_version >= min_version:  # TODO: Use semver
                needs_update = False

        if needs_update:
            print(f"Updating {package}...")
            subprocess.run(["npm", "install", package, "--save-dev"], check=True)
            return True

        return False

    def setup(self, config: Dict[str, Any]) -> None:
        self.__list_installed_versions()

        # eslint
        self.__npm_install("eslint", EslintTool.MIN_ESLINT_VERSION)

        # On some systems it is necessary to update the install-peerdeps package
        # for npx install-peerdeps to operate
        self.__npm_install("install-peerdeps", EslintTool.MIN_PEERDEPS_VERSION)

        # eslint-config-airbnb
        if self.__npm_install("eslint-config-airbnb", EslintTool.MIN_AIRBNB_VERSION):
            self.exec(
                ["npx", "install-peerdeps", "--dev", "eslint-config-airbnb"], check=True
            )

        # install react plugin if necessary
        project_react_version = self.installed_versions.get("react", None)
        if project_react_version is not None:
            self.__npm_install("eslint-plugin-react", EslintTool.MIN_REACT_VERSION)

        # install .eslintrc.yml
        if not os.path.exists(
            os.path.join(self.base_path, EslintTool.CONFIG_FILE_NAME)
        ):
            print(f"Installing {EslintTool.CONFIG_FILE_NAME}...")

            if project_react_version is not None:
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
            ".",
        ]
        for f in files:
            cmd.append(f)
        result = self.exec(cmd, capture_output=True)
        # Return codes:
        # 0 = no violations, 1 = violations, 2+ = tool failure
        if result.returncode > 1:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
        return result.stdout.rstrip()
