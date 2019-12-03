from pathlib import Path

from click.testing import CliRunner

import util
from _pytest.monkeypatch import MonkeyPatch
from bento.commands.check import check
from bento.commands.init import (
    _install_config_if_not_exists,
    _install_ignore_if_not_exists,
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
        _install_config_if_not_exists(context)
        cfg = context.config
        assert "r2c.eslint" in cfg["tools"]
        assert "r2c.flake8" in cfg["tools"]
        assert "r2c.bandit" in cfg["tools"]


def test_no_install_empty_project() -> None:
    """Validates that bento does not install a config on an empty project"""
    context = Context(base_path=INTEGRATION / "none")
    # pytest.raises() does not catch SystemExit, so use try/except here
    try:
        _install_config_if_not_exists(context)
    except SystemExit as ex:
        assert isinstance(ex, SystemExit)
    assert not context.config_path.exists()


def test_install_ignore_in_repo() -> None:
    """Validates that bento installs an ignore file if none exists"""
    context = Context(base_path=SIMPLE, is_init=True)
    with util.mod_file(context.ignore_file_path):
        context.ignore_file_path.unlink()
        _install_ignore_if_not_exists(context)
        context = Context(base_path=SIMPLE, is_init=True)
        ig = context.file_ignores
        assert "node_modules/" in ig.patterns


def test_install_ignore_no_repo(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Validates that bento installs extra ignore items when not in a git repo"""
    monkeypatch.chdir(tmp_path)

    context = Context(base_path=tmp_path, is_init=True)
    _install_ignore_if_not_exists(context)
    context = Context(base_path=tmp_path, is_init=True)
    ig = context.file_ignores
    assert "node_modules/" in ig.patterns


def test_init_already_setup() -> None:
    context = Context(base_path=SIMPLE)
    result = CliRunner(mix_stderr=False).invoke(init, obj=context)

    expectation = """╭──────────────────────────────────────────────────────────────────────────────╮
│                             Bento Initialization                             │
╰──────────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────────────────────────────────╮
│                            Project Identification                            │
╰──────────────────────────────────────────────────────────────────────────────╯

Detected project with Python and node-js (with react)

Bento archive is already configured on this project.

To use Bento:
  view archived results                    $ bento check --show-all
  check a specific path                    $ bento check [PATH]
  disable a check                          $ bento disable check [TOOL] [CHECK]
  get help about a command                 $ bento [COMMAND] --help

╭──────────────────────────────────────────────────────────────────────────────╮
│                                  Thank You                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
Bento is initialized!

Please add Bento to version control:

  $ git add .gitignore .bento?* && git commit -m 'Add Bento to project'

Need help or want to share feedback? Reach out to us at support@r2c.dev or file
an issue on GitHub. We’d love to hear from you!

Join #bento in our community Slack for support, to talk with other users, and
share feedback.

From all of us at r2c, thank you for trying Bento! We can’t wait to hear what
you think.

"""

    assert result.stderr == expectation


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
    """Validates that `init --clean` deletes tool virtual environments"""
    context = Context(base_path=INTEGRATION / "py-only")
    venv_file = INTEGRATION / "py-only" / ".bento" / "flake8" / "bin" / "activate"

    # Ensure venv is created
    CliRunner(mix_stderr=False).invoke(check, obj=context)
    assert venv_file.exists()

    # Ensure venv is corrupted, and not fixed with standard check
    venv_file.unlink()
    CliRunner(mix_stderr=False).invoke(check, obj=context)
    assert not venv_file.exists()

    # Ensure `init --clean` followed by `check` recreates venv
    CliRunner(mix_stderr=False).invoke(init, obj=context, args=["--clean"])
    CliRunner(mix_stderr=False).invoke(check, obj=context)
    assert venv_file.exists()
