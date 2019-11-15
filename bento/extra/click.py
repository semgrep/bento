from typing import Type

from bento.base_context import BaseContext
from bento.extra.flake8 import Flake8Parser, Flake8Tool
from bento.parser import Parser
from bento.tool import StrTool


class ClickParser(Flake8Parser):
    @staticmethod
    def id_to_link(check_id: str) -> str:
        return ""

    @staticmethod
    def tool() -> Type[StrTool]:
        return ClickTool


class ClickTool(Flake8Tool):
    TOOL_ID = "r2c.click"  # to-do: versioning?
    VENV_DIR = "click"
    PACKAGES = {"flake8": "3.7.0", "flake8-json": "19.8.0", "flake8-click": "0.2.0"}

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return False

    @property
    def parser_type(self) -> Type[Parser]:
        return ClickParser

    @classmethod
    def tool_id(cls) -> str:
        return cls.TOOL_ID

    def select_clause(self) -> str:
        return "--select=CLC"
