from pathlib import Path

from click.testing import CliRunner

import bento.extra.eslint
import bento.result
import bento.tool_runner
import util
from bento.commands.archive import archive
from bento.context import Context

INTEGRATION = Path(__file__).parent.parent / "integration"


def test_archive_no_init() -> None:
    """Validates that archive fails when no configuration file"""

    runner = CliRunner()
    # No .bento.yml exists in this directory
    result = runner.invoke(archive, obj=Context(base_path=INTEGRATION))
    assert result.exit_code == 3


def test_archive_updates_whitelist() -> None:
    """Validates that archive updates the whitelist file"""

    runner = CliRunner()

    context = Context(INTEGRATION / "simple")

    with util.mod_file(context.baseline_file_path) as whitelist:
        runner.invoke(archive, obj=context)
        yml = bento.result.yml_to_violation_hashes(whitelist)

    expectation = {
        "r2c.bandit": {
            "d546320ff6d704181f23ed6653971025",
            "6f77d9d773cc5248ae20b83f80a7b26a",
        },
        "r2c.eslint": {"6daebd293be00a3d97e19de4a1a39fa5"},
        "r2c.flake8": {
            "27a91174ddbf5e932a1b2cdbd57da9e0",
            "77e04010d3b0256fd3a434cd00f2c944",
        },
    }

    assert yml == expectation
