from typing import Type

from semantic_version import SimpleSpec

from bento.extra.flake8 import Flake8Parser, Flake8Tool
from bento.parser import Parser
from bento.tool import StrTool

PREFIX = "r2c-boto3-"


class Boto3Parser(Flake8Parser):
    @staticmethod
    def id_to_link(check_id: str) -> str:
        page = Boto3Parser.id_to_name(check_id)
        return f"https://checks.bento.dev/en/latest/flake8-boto3/{page}"

    @staticmethod
    def id_to_name(check_id: str) -> str:
        return check_id.replace(PREFIX, "")

    @staticmethod
    def tool() -> Type[StrTool]:
        return Boto3Tool


class Boto3Tool(Flake8Tool):
    TOOL_ID = "r2c.boto3"
    VENV_DIR = "boto3"
    PACKAGES = {
        "flake8": SimpleSpec("~=3.7.0"),
        "flake8-json": SimpleSpec("~=19.8.0"),
        "flake8-boto3": SimpleSpec("~=0.2.4"),
    }

    @property
    def parser_type(self) -> Type[Parser]:
        return Boto3Parser

    @classmethod
    def tool_id(cls) -> str:
        return cls.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Checks for the AWS boto3 library in Python"

    def select_clause(self) -> str:
        return "--select={}".format(PREFIX)
