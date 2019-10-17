import os

from click.testing import CliRunner

import bento.extra.eslint
import bento.result
import bento.tool_runner
import util
from _pytest.monkeypatch import MonkeyPatch
from bento.commands.archive import archive
from bento.context import Context

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../.."))


def test_archive_no_init(monkeypatch: MonkeyPatch) -> None:
    """Validates that archive fails when no configuration file"""

    runner = CliRunner()
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration"))
    # No .bento.yml exists in this directory
    result = runner.invoke(archive, obj=Context())
    assert result.exit_code == 3


def test_archive_updates_whitelist(monkeypatch: MonkeyPatch) -> None:
    """Validates that archive updates the whitelist file"""

    runner = CliRunner()

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.BASELINE_FILE_PATH) as whitelist:
        runner.invoke(archive, obj=Context())
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
