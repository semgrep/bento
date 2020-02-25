from typing import Iterable, Type

from bento.extra.bandit import BanditTool
from bento.extra.boto3 import Boto3Tool
from bento.extra.click import ClickTool
from bento.extra.dlint import DlintTool
from bento.extra.eslint import EslintTool
from bento.extra.flake8 import Flake8Tool
from bento.extra.flask import FlaskTool
from bento.extra.grep import GrepTool
from bento.extra.hadolint import HadolintTool
from bento.extra.jinjalint import JinjalintTool
from bento.extra.python_taint import PythonTaintTool
from bento.extra.r2c_check_registry import SgrepR2cCheckRegistryTool
from bento.extra.requests import RequestsTool
from bento.extra.sgrep import SGrepTool
from bento.extra.shellcheck import ShellcheckTool
from bento.tool import Tool

TOOLS: Iterable[Type[Tool]] = [
    BanditTool,
    Boto3Tool,
    ClickTool,
    DlintTool,
    EslintTool,
    FlaskTool,
    Flake8Tool,
    GrepTool,
    HadolintTool,
    JinjalintTool,
    # PyreTool,  # Pyre does not work with explicit paths
    RequestsTool,
    SGrepTool,
    ShellcheckTool,
    PythonTaintTool,
    SgrepR2cCheckRegistryTool,
]
