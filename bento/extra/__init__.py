from typing import Iterable, Type

from bento.extra.bandit import BanditTool
from bento.extra.click import ClickTool
from bento.extra.eslint import EslintTool
from bento.extra.flake8 import Flake8Tool
from bento.extra.flask import FlaskTool
from bento.extra.grep import GrepTool
from bento.extra.hadolint import HadolintTool
from bento.extra.pyre import PyreTool
from bento.extra.requests import RequestsTool
from bento.extra.sgrep import SGrepTool
from bento.extra.shellcheck import ShellcheckTool
from bento.tool import Tool

TOOLS: Iterable[Type[Tool]] = [
    BanditTool,
    ClickTool,
    EslintTool,
    FlaskTool,
    Flake8Tool,
    GrepTool,
    HadolintTool,
    PyreTool,
    RequestsTool,
    SGrepTool,
    ShellcheckTool,
]
