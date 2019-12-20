from pathlib import Path

from click.testing import CliRunner

import util
from bento.commands.disable import disable
from bento.commands.enable import enable
from bento.context import Context

INTEGRATION = Path(__file__).parent.parent / "integration"
SIMPLE = INTEGRATION / "simple"
PY_ONLY = INTEGRATION / "py-only"


def test_disable_tool_found() -> None:
    """Validates that disabling a check updates ignores in config"""

    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        runner.invoke(disable, ["check", "r2c.eslint", "foo"], obj=context)
        config = context.config
        assert "foo" in config["tools"]["r2c.eslint"]["ignore"]


def test_disable_tool_not_found() -> None:
    """Validates that disabling an unconfigured tool causes run failure"""

    runner = CliRunner()
    context = Context(base_path=PY_ONLY)

    result = runner.invoke(disable, ["check", "r2c.eslint", "foo"], obj=context)
    assert result.exit_code == 3


def test_enable_tool_found() -> None:
    """Validates that enabling a check updates ignores in config"""

    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        runner.invoke(enable, ["check", "r2c.eslint", "curly"], obj=context)
        config = context.config
        assert "curly" not in config["tools"]["r2c.eslint"]["ignore"]


def test_enable_tool_not_found() -> None:
    """Validates that enabling an unconfigured tool causes run failure"""

    runner = CliRunner()
    context = Context(base_path=PY_ONLY)

    result = runner.invoke(enable, ["check", "r2c.eslint", "foo"], obj=context)
    assert result.exit_code == 3


def test_disable_tool() -> None:
    """Validates that disable tool correctly modifies config"""
    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        runner.invoke(disable, ["tool", "r2c.eslint"], obj=context)
        config = context.config
        assert config["tools"]["r2c.eslint"]["run"] is False

        # Check persists to file (Context reads from file)
        persisted_config = Context(base_path=SIMPLE).config
        assert persisted_config["tools"]["r2c.eslint"]["run"] is False


def test_enable_tool() -> None:
    """Validates that enable tool works with no run"""
    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        config = context.config
        assert "run" not in config["tools"]["r2c.eslint"]

        runner.invoke(enable, ["tool", "r2c.eslint"], obj=context)

        context = Context(base_path=SIMPLE)
        assert config["tools"]["r2c.eslint"]["run"]

        # Check persists to file (Context reads from file)
        persisted_config = Context(base_path=SIMPLE).config
        assert persisted_config["tools"]["r2c.eslint"]["run"]


def test_enable_invalid_tool() -> None:
    """Validates that enable tool exits when invalid tool is passed"""
    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        config = context.config
        assert "run" not in config["tools"]["r2c.eslint"]

        result = runner.invoke(enable, ["tool", "nonexistent"], obj=context)
        assert result.exit_code == 3


def test_disable_then_enable_tool() -> None:
    """Validates that enable tool works after previously disabling"""
    runner = CliRunner()
    context = Context(base_path=SIMPLE)

    with util.mod_file(context.config_path):
        config = context.config

        runner.invoke(disable, ["tool", "r2c.eslint"], obj=context)
        assert config["tools"]["r2c.eslint"]["run"] is False

        runner.invoke(enable, ["tool", "r2c.eslint"], obj=context)
        assert config["tools"]["r2c.eslint"]["run"]

        # Check persists to file (Context reads from file)
        persisted_config = Context(base_path=SIMPLE).config
        assert persisted_config["tools"]["r2c.eslint"]["run"]


def test_enable_default_ignores() -> None:
    """Validates that enable tool not in config uses default ignores"""
    runner = CliRunner()
    context = Context(base_path=PY_ONLY)

    with util.mod_file(context.config_path):
        config = context.config
        # Test is meaningless if tool is already in config
        assert "r2c.eslint" not in config["tools"]

        runner.invoke(enable, ["tool", "r2c.eslint"], obj=context)
        assert config["tools"]["r2c.eslint"]["run"]
        assert len(config["tools"]["r2c.eslint"]["ignore"]) > 0

        # Check persists to file (Context reads from file)
        persisted_config = Context(base_path=PY_ONLY).config
        assert persisted_config["tools"]["r2c.eslint"]["run"]
        assert len(persisted_config["tools"]["r2c.eslint"]["ignore"]) > 0
