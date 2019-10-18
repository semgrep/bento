from typing import Iterable, Type

from bento.extra.bandit import BanditTool
from bento.extra.eslint import EslintTool
from bento.extra.flake8 import Flake8Tool
from bento.extra.pyre import PyreTool
from bento.tool import Tool

TOOLS: Iterable[Type[Tool]] = [BanditTool, EslintTool, Flake8Tool, PyreTool]
