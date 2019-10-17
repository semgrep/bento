import os

from click.testing import CliRunner

import util
from _pytest.monkeypatch import MonkeyPatch
from bento.commands.init import __install_config_if_not_exists, init
from bento.context import Context

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../.."))


def test_install_config(monkeypatch: MonkeyPatch) -> None:
    """Validates that bento installs a config file if none exists"""
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))
    with util.mod_file(".bento.yml"):
        os.remove(".bento.yml")
        context = Context()
        __install_config_if_not_exists(context)
        cfg = context.config
        assert "r2c.eslint" in cfg["tools"]
        assert "r2c.flake8" in cfg["tools"]
        assert "r2c.bandit" in cfg["tools"]


def test_init_already_setup(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    result = CliRunner(mix_stderr=False).invoke(init, obj=Context())

    expectation = "Detected project with Python and node-js\n\n✔ Bento is initialized on your project."
    assert result.stderr.strip() == expectation


def test_init_js_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/js-and-ts"))

    with util.mod_file(".bento.yml"):
        os.remove(".bento.yml")
        CliRunner(mix_stderr=False).invoke(init, obj=Context())
        config = Context().config

    assert "r2c.eslint" in config["tools"]
    assert "r2c.flake8" not in config["tools"]
    assert "r2c.bandit" not in config["tools"]


def test_init_py_only(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/py-only"))

    with util.mod_file(".bento.yml"):
        os.remove(".bento.yml")
        CliRunner(mix_stderr=False).invoke(init, obj=Context())
        config = Context().config

    assert "r2c.eslint" not in config["tools"]
    assert "r2c.flake8" in config["tools"]
    assert "r2c.bandit" in config["tools"]
