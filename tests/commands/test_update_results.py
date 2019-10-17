import os

from click.testing import CliRunner

import bento.extra.eslint
import bento.result
import bento.tool_runner
import util
from _pytest.monkeypatch import MonkeyPatch
from bento.commands.update_ignores import disable, enable
from bento.context import Context

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../.."))


def test_disable_tool_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that disabling a check updates ignores in config"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.CONFIG_PATH):
        runner.invoke(disable, ["r2c.eslint", "foo"], obj=Context())
        config = bento.context.Context().config
        assert "foo" in config["tools"]["r2c.eslint"]["ignore"]


def test_disable_tool_not_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that disabling an unconfigured tool causes run failure"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/py-only"))

    result = runner.invoke(disable, ["r2c.eslint", "foo"], obj=Context())
    assert result.exit_code == 3


def test_enable_tool_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that enabling a check updates ignores in config"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.CONFIG_PATH):
        runner.invoke(enable, ["r2c.eslint", "curly"], obj=Context())
        config = bento.context.Context().config
        assert "curly" not in config["tools"]["r2c.eslint"]["ignore"]


def test_enable_tool_not_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that enabling an unconfigured tool causes run failure"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/py-only"))

    result = runner.invoke(enable, ["r2c.eslint", "foo"], obj=Context())
    assert result.exit_code == 3
