from typing import Dict, List, Type

from bento.extra.bandit import BanditTool
from bento.extra.eslint import EslintTool
from bento.extra.flake8 import Flake8Tool
from bento.tool import Tool

__tool_list: List[Type[Tool]] = [BanditTool, EslintTool, Flake8Tool]

TOOLS: Dict[str, Type[Tool]] = {t.tool_id(): t for t in __tool_list}
