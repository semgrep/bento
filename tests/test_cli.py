import json
import os
from typing import Any, Collection, Dict, List, Optional

from click.testing import CliRunner

import bento.cli
import bento.extra.eslint
import bento.result
import bento.tool_runner
import util
from _pytest.monkeypatch import MonkeyPatch
from bento.context import Context
from bento.tool import Tool

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, ".."))


def test_install_config(monkeypatch: MonkeyPatch) -> None:
    """Validates that bento installs a config file if none exists"""
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))
    with util.mod_file(".bento.yml"):
        os.remove(".bento.yml")
        context = Context()
        bento.cli.__install_config_if_not_exists(context)
        cfg = context.config
        assert "r2c.eslint" in cfg["tools"]
        assert "r2c.flake8" in cfg["tools"]
        assert "r2c.bandit" in cfg["tools"]


def test_archive_no_init(monkeypatch: MonkeyPatch) -> None:
    """Validates that archive fails when no configuration file"""

    runner = CliRunner()
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration"))
    # No .bento.yml exists in this directory
    result = runner.invoke(bento.cli.archive, obj=Context())
    assert result.exit_code == 3


def test_archive_updates_whitelist(monkeypatch: MonkeyPatch) -> None:
    """Validates that archive updates the whitelist file"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.BASELINE_FILE_PATH) as whitelist:
        runner.invoke(bento.cli.archive, obj=Context())
        yml = bento.result.yml_to_violation_hashes(whitelist)

    expectation = {
        "r2c.bandit": {
            "d546320ff6d704181f23ed6653971025",
            "6f77d9d773cc5248ae20b83f80a7b26a",
        },
        "r2c.eslint": {"6daebd293be00a3d97e19de4a1a39fa5"},
        "r2c.flake8": {
            "27a91174ddbf5e932a1b2cdbd57da9e0",
            "47e9ffd6dfd406278ca564f05117f22b",
        },
    }

    assert yml == expectation


def test_disable_tool_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that disabling a check updates ignores in config"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.CONFIG_PATH):
        runner.invoke(bento.cli.disable, ["r2c.eslint", "foo"], obj=Context())
        config = bento.context.Context().config
        assert "foo" in config["tools"]["r2c.eslint"]["ignore"]


def test_disable_tool_not_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that disabling an unconfigured tool causes run failure"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/py-only"))

    result = runner.invoke(bento.cli.disable, ["r2c.eslint", "foo"], obj=Context())
    assert result.exit_code == 3


def test_enable_tool_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that enabling a check updates ignores in config"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.CONFIG_PATH):
        runner.invoke(bento.cli.enable, ["r2c.eslint", "curly"], obj=Context())
        config = bento.context.Context().config
        assert "curly" not in config["tools"]["r2c.eslint"]["ignore"]


def test_enable_tool_not_found(monkeypatch: MonkeyPatch) -> None:
    """Validates that enabling an unconfigured tool causes run failure"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/py-only"))

    result = runner.invoke(bento.cli.enable, ["r2c.eslint", "foo"], obj=Context())
    assert result.exit_code == 3


def test_check_happy_path(monkeypatch: MonkeyPatch) -> None:
    """Validates that check discovers issues in normal usage"""

    runner = CliRunner(mix_stderr=False)

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    result = runner.invoke(
        bento.cli.check, ["--formatter", "bento.formatter.Json"], obj=Context()
    )
    parsed = json.loads(result.stdout)
    assert len(parsed) == 4


def test_check_no_archive(monkeypatch: MonkeyPatch) -> None:
    """Validates that check operates without an archive file"""

    runner = CliRunner(mix_stderr=False)

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.BASELINE_FILE_PATH):
        os.remove(bento.constants.BASELINE_FILE_PATH)
        result = runner.invoke(
            bento.cli.check, ["--formatter", "bento.formatter.Json"], obj=Context()
        )
        parsed = json.loads(result.stdout)
        assert len(parsed) == 5  # Archive contains a single whitelisted finding


def test_check_no_init(monkeypatch: MonkeyPatch) -> None:
    """Validates that check fails when no configuration file"""

    runner = CliRunner()
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration"))
    # No .bento.yml exists in this directory
    result = runner.invoke(bento.cli.check, obj=Context())
    assert result.exit_code == 3


def test_check_tool_error(monkeypatch: MonkeyPatch) -> None:
    expectation = "✘ Error while running r2c.foo: test"

    def mock_results(
        self: bento.tool_runner.Runner,
        tools: Collection[Tool],
        config: Dict[str, Any],
        baseline: bento.result.Baseline,
        files: Optional[List[str]],
    ) -> Collection[bento.tool_runner.RunResults]:
        return [("r2c.foo", Exception("test"))]

    monkeypatch.setattr(bento.tool_runner.Runner, "parallel_results", mock_results)
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    runner = CliRunner(mix_stderr=False)

    result = runner.invoke(bento.cli.check, obj=Context())
    assert result.exit_code == 3
    assert expectation in result.stderr.splitlines()


def test_init_already_setup(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    result = CliRunner(mix_stderr=False).invoke(bento.cli.init, obj=Context())

    expectation = "Detected project with Python and node-js\n\n✔ Bento is initialized on your project."
    assert result.stderr.strip() == expectation


def test_init_js_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/js-and-ts"))

    with util.mod_file(".bento.yml"):
        os.remove(".bento.yml")
        CliRunner(mix_stderr=False).invoke(bento.cli.init, obj=Context())
        config = Context().config

    assert "r2c.eslint" in config["tools"]
    assert "r2c.flake8" not in config["tools"]
    assert "r2c.bandit" not in config["tools"]


def test_init_py_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/py-only"))

    with util.mod_file(".bento.yml"):
        os.remove(".bento.yml")
        CliRunner(mix_stderr=False).invoke(bento.cli.init, obj=Context())
        config = Context().config

    assert "r2c.eslint" not in config["tools"]
    assert "r2c.flake8" in config["tools"]
    assert "r2c.bandit" in config["tools"]
