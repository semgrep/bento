from pathlib import Path

from click.testing import CliRunner

import util
from _pytest.monkeypatch import MonkeyPatch
from bento.commands.init import (
    __install_config_if_not_exists,
    __install_ignore_if_not_exists,
    init,
)
from bento.context import Context

INTEGRATION = Path(__file__).parent.parent / "integration"
SIMPLE = INTEGRATION / "simple"


def test_install_config() -> None:
    """Validates that bento installs a config file if none exists"""
    context = Context(base_path=SIMPLE)
    with util.mod_file(context.config_path):
        context.config_path.unlink()
        __install_config_if_not_exists(context)
        cfg = context.config
        assert "r2c.eslint" in cfg["tools"]
        assert "r2c.flake8" in cfg["tools"]
        assert "r2c.bandit" in cfg["tools"]


def test_install_ignore_in_repo() -> None:
    """Validates that bento installs an ignore file if none exists"""
    context = Context(base_path=SIMPLE, is_init=True)
    with util.mod_file(context.ignore_file_path):
        context.ignore_file_path.unlink()
        __install_ignore_if_not_exists(context)
        context = Context(base_path=SIMPLE, is_init=True)
        ig = context.file_ignores
        assert "node_modules/" in ig.patterns


def test_install_ignore_no_repo(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Validates that bento installs extra ignore items when not in a git repo"""
    monkeypatch.chdir(tmp_path)

    context = Context(base_path=tmp_path, is_init=True)
    __install_ignore_if_not_exists(context)
    context = Context(base_path=tmp_path, is_init=True)
    ig = context.file_ignores
    assert "node_modules/" in ig.patterns


def test_init_already_setup() -> None:
    context = Context(base_path=SIMPLE)
    result = CliRunner(mix_stderr=False).invoke(init, obj=context)

    expectation = "Detected project with Python and node-js (with react)\n\n✔ Bento is initialized on your project."
    assert result.stderr.strip() == expectation


def test_init_js_only() -> None:
    context = Context(base_path=INTEGRATION / "js-and-ts")
    with util.mod_file(context.config_path):
        context.config_path.unlink()
        CliRunner(mix_stderr=False).invoke(init, obj=context)
        config = context.config

    assert "r2c.eslint" in config["tools"]
    assert "r2c.flake8" not in config["tools"]
    assert "r2c.bandit" not in config["tools"]


def test_init_py_only() -> None:
    context = Context(base_path=INTEGRATION / "py-only")
    with util.mod_file(context.config_path):
        context.config_path.unlink()
        CliRunner(mix_stderr=False).invoke(init, obj=context)
        config = context.config

    assert "r2c.eslint" not in config["tools"]
    assert "r2c.flake8" in config["tools"]
    assert "r2c.bandit" in config["tools"]


def test_init_clean() -> None:
    """Validates that `init --clean` recreates tool virtual environments"""
    context = Context(base_path=INTEGRATION / "py-only")
    venv_file = INTEGRATION / "py-only" / ".bento" / "flake8" / "bin" / "activate"

    # Ensure venv is created
    CliRunner(mix_stderr=False).invoke(init, obj=context)
    assert venv_file.exists()

    # Ensure venv is corrupted, and not fixed with standard init
    venv_file.unlink()
    CliRunner(mix_stderr=False).invoke(init, obj=context)
    assert not venv_file.exists()

    # Ensure --clean recreates venv
    CliRunner(mix_stderr=False).invoke(init, obj=context, args=["--clean"])
    assert venv_file.exists()
