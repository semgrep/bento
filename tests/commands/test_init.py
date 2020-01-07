from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from _pytest.monkeypatch import MonkeyPatch
from bento.commands.check import check
from bento.commands.init import InitCommand, init
from bento.context import Context
from tests.util import mod_file

INTEGRATION = Path(__file__).parent.parent / "integration"
SIMPLE = INTEGRATION / "simple"


def test_install_config() -> None:
    """Validates that bento installs a config file if none exists"""
    context = Context(base_path=SIMPLE)
    command = InitCommand(context)
    with mod_file(context.config_path):
        context.config_path.unlink()
        command._install_config_if_not_exists()
        cfg = context.config
        assert "r2c.eslint" in cfg["tools"]
        assert "r2c.flake8" in cfg["tools"]
        assert "r2c.bandit" in cfg["tools"]


def test_no_install_empty_project() -> None:
    """Validates that bento does installs a config on an empty project"""
    context = Context(base_path=INTEGRATION / "none")
    command = InitCommand(context)
    with mod_file(context.config_path):
        context.config_path.unlink()
        assert not context.config_path.exists()
        command._install_config_if_not_exists()
        assert len(context.config["tools"]) == 0


def test_install_ignore_in_repo() -> None:
    """Validates that bento installs an ignore file if none exists"""
    context = Context(base_path=SIMPLE, is_init=True)
    command = InitCommand(context)
    with mod_file(context.ignore_file_path):
        context.ignore_file_path.unlink()
        command._install_ignore_if_not_exists()
        context = Context(base_path=SIMPLE, is_init=True)
        ig = context.file_ignores
        assert "node_modules/" in ig.patterns


def test_install_ignore_no_repo(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Validates that bento installs extra ignore items when not in a git repo"""
    monkeypatch.chdir(tmp_path)

    context = Context(base_path=tmp_path, is_init=True)
    command = InitCommand(context)
    command._install_ignore_if_not_exists()
    context = Context(base_path=tmp_path, is_init=True)
    ig = context.file_ignores
    assert "node_modules/" in ig.patterns


def test_init_already_setup() -> None:
    context = Context(base_path=SIMPLE)
    result = CliRunner(mix_stderr=False).invoke(init, obj=context)

    expectation = """
╭──────────────────────────────────────────────────────────────────────────────╮
│                             Bento Initialization                             │
╰──────────────────────────────────────────────────────────────────────────────╯
Creating default ignore file at .bentoignore․․․․․․․․․․․․․․․․․․․․․ 👋 Skipped   
Creating default configuration at .bento/config.yml․․․․․․․․․․․․․․ 👋 Skipped   

Detected project with Python and node-js (with react)


╭──────────────────────────────────────────────────────────────────────────────╮
│                                  Next Steps                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
Bento is at its best when it runs automatically, either in CI or as a git hook.
To learn more about these, see Bento in CI or Bento as a Git Hook in our
README.

To use Bento:
  check project․․․․․․․․․․․․․․․․․․․․․․․․․․․ $ bento check
  view archived results․․․․․․․․․․․․․․․․․․․ $ bento check --show-all
  disable a check․․․․․․․․․․․․․․․․․․․․․․․․․ $ bento disable check [TOOL] [CHECK]
  enable a tool․․․․․․․․․․․․․․․․․․․․․․․․․․․ $ bento enable tool [TOOL]
  install commit hook․․․․․․․․․․․․․․․․․․․․․ $ bento install-hook
  get help for a command․․․․․․․․․․․․․․․․․․ $ bento [COMMAND] --help


╭──────────────────────────────────────────────────────────────────────────────╮
│                                  Thank You                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
From all of us at r2c, thank you for trying Bento! We can’t wait to hear what
you think.

Help and feedback: Reach out to us at support@r2c.dev or file an issue on
GitHub. We’d love to hear from you!

Community: Join #bento on our community Slack. Get support, talk with other
users, and share feedback.

"""  # noqa - above string purposely contains trailing whitespace

    print(result.stderr)
    assert result.stderr == expectation


def test_init_js_only() -> None:
    context = Context(base_path=INTEGRATION / "js-and-ts")
    with mod_file(context.config_path):
        context.config_path.unlink()
        CliRunner(mix_stderr=False).invoke(init, obj=context)
        config = context.config

    assert "r2c.eslint" in config["tools"]
    assert "r2c.flake8" not in config["tools"]
    assert "r2c.bandit" not in config["tools"]


def test_init_py_only() -> None:
    context = Context(base_path=INTEGRATION / "py-only")
    with mod_file(context.config_path):
        context.config_path.unlink()
        CliRunner(mix_stderr=False).invoke(init, obj=context)
        config = context.config

    assert "r2c.eslint" not in config["tools"]
    assert "r2c.flake8" in config["tools"]
    assert "r2c.bandit" in config["tools"]


def test_init_clean(tmp_path: Path) -> None:
    """Validates that `init --clean` deletes tool virtual environments"""
    context = Context(base_path=INTEGRATION / "py-only")

    with patch("bento.constants.VENV_PATH", new=tmp_path):
        venv_file = tmp_path / "flake8" / "bin" / "activate"

        # Ensure venv is created
        CliRunner(mix_stderr=False).invoke(check, obj=context)
        assert venv_file.exists()

        # Ensure venv is corrupted, and not fixed with standard check
        venv_file.unlink()
        CliRunner(mix_stderr=False).invoke(check, obj=context)
        assert not venv_file.exists()

        # Ensure `init --clean` followed by `check` recreates venv
        CliRunner(mix_stderr=False).invoke(init, obj=context, args=["--clean"])
        assert not tmp_path.exists()
        CliRunner(mix_stderr=False).invoke(check, obj=context)
        assert venv_file.exists()
