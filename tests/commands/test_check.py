import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

import bento.extra.eslint
import bento.result
import bento.tool_runner
import util
from bento.commands.check import check
from bento.context import Context

INTEGRATION = Path(__file__).parent.parent / "integration"
SIMPLE = Path(__file__).parent.parent / "integration/simple"


def test_check_happy_path() -> None:
    """Validates that check discovers issues in normal usage"""

    runner = CliRunner(mix_stderr=False)
    Context(SIMPLE).cache.wipe()

    result = runner.invoke(
        check, ["--formatter", "json"], obj=Context(base_path=SIMPLE)
    )
    parsed = json.loads(result.stdout)
    assert len(parsed) == 4


def test_check_specified_paths() -> None:
    """Validates that check discovers issues in specified paths"""

    runner = CliRunner(mix_stderr=False)
    Context(SIMPLE).cache.wipe()

    result = runner.invoke(
        check,
        ["--formatter", "json", "init.js", "foo.py"],
        obj=Context(base_path=SIMPLE),
    )
    parsed = json.loads(result.stdout)
    assert len(parsed) == 3


def test_check_specified_paths_and_staged() -> None:
    """Validates that check errors when --staged-only used with paths"""

    runner = CliRunner(mix_stderr=False)
    Context(SIMPLE).cache.wipe()

    try:
        runner.invoke(
            check,
            ["--staged-only", "init.js", "foo.py"],
            obj=Context(base_path=SIMPLE),
            catch_exceptions=False,
        )
        assert False
    except Exception:
        pass


def test_check_no_archive() -> None:
    """Validates that check operates without an archive file"""

    runner = CliRunner(mix_stderr=False)
    context = Context(base_path=SIMPLE)
    context.cache.wipe()

    with util.mod_file(context.baseline_file_path):
        context.baseline_file_path.unlink()
        result = runner.invoke(
            check, ["--formatter", "json"], obj=Context(base_path=SIMPLE)
        )
        parsed = json.loads(result.stdout)
        assert len(parsed) == 5  # Archive contains a single whitelisted finding


def test_check_no_init() -> None:
    """Validates that check fails when no configuration file"""

    runner = CliRunner()
    Context(INTEGRATION).cache.wipe()
    # No .bento.yml exists in this directory
    result = runner.invoke(check, obj=Context(base_path=INTEGRATION))
    assert result.exit_code == 3


def test_check_tool_error() -> None:
    expectation = "✘ Error while running r2c.foo: test"

    with patch.object(
        bento.tool_runner.Runner,
        "parallel_results",
        return_value=[("r2c.foo", Exception("test"))],
    ):
        runner = CliRunner(mix_stderr=False)
        Context(SIMPLE).cache.wipe()

        result = runner.invoke(check, obj=Context(base_path=SIMPLE))
        assert result.exit_code == 3
        assert expectation in result.stderr.splitlines()
