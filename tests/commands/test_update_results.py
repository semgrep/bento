from pathlib import Path

from click.testing import CliRunner

import util
from bento.commands.update_ignores import disable, enable
from bento.context import Context

INTEGRATION = Path(__file__).parent.parent / "integration"
SIMPLE = INTEGRATION / "simple"
PY_ONLY = INTEGRATION / "py-only"


def test_disable_tool_found() -> None:
    """Validates that disabling a check updates ignores in config"""

    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        runner.invoke(disable, ["r2c.eslint", "foo"], obj=context)
        config = context.config
        assert "foo" in config["tools"]["r2c.eslint"]["ignore"]


def test_disable_tool_not_found() -> None:
    """Validates that disabling an unconfigured tool causes run failure"""

    runner = CliRunner()
    context = Context(base_path=PY_ONLY)

    result = runner.invoke(disable, ["r2c.eslint", "foo"], obj=context)
    assert result.exit_code == 3


def test_enable_tool_found() -> None:
    """Validates that enabling a check updates ignores in config"""

    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        runner.invoke(enable, ["r2c.eslint", "curly"], obj=context)
        config = context.config
        assert "curly" not in config["tools"]["r2c.eslint"]["ignore"]


def test_enable_tool_not_found() -> None:
    """Validates that enabling an unconfigured tool causes run failure"""

    runner = CliRunner()
    context = Context(base_path=PY_ONLY)

    result = runner.invoke(enable, ["r2c.eslint", "foo"], obj=context)
    assert result.exit_code == 3
