import json
import os
from typing import Any, Collection, Dict, List, Optional

from click.testing import CliRunner

import bento.extra.eslint
import bento.result
import bento.tool_runner
import util
from _pytest.monkeypatch import MonkeyPatch
from bento.commands.check import check
from bento.context import Context
from bento.tool import Tool

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, "../.."))


def test_check_happy_path(monkeypatch: MonkeyPatch) -> None:
    """Validates that check discovers issues in normal usage"""

    runner = CliRunner(mix_stderr=False)

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    result = runner.invoke(
        check, ["--formatter", "bento.formatter.Json"], obj=Context()
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
            check, ["--formatter", "bento.formatter.Json"], obj=Context()
        )
        parsed = json.loads(result.stdout)
        assert len(parsed) == 5  # Archive contains a single whitelisted finding


def test_check_no_init(monkeypatch: MonkeyPatch) -> None:
    """Validates that check fails when no configuration file"""

    runner = CliRunner()
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration"))
    # No .bento.yml exists in this directory
    result = runner.invoke(check, obj=Context())
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

    result = runner.invoke(check, obj=Context())
    assert result.exit_code == 3
    assert expectation in result.stderr.splitlines()
