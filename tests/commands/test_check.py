import json
import os
from typing import Collection, List, Optional

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

    result = runner.invoke(check, ["--formatter", "json"], obj=Context())
    print(result.stderr)
    parsed = json.loads(result.stdout)
    assert len(parsed) == 4


def test_check_specified_paths(monkeypatch: MonkeyPatch) -> None:
    """Validates that check discovers issues in specified paths"""

    runner = CliRunner(mix_stderr=False)

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    result = runner.invoke(
        check, ["--formatter", "json", "init.js", "foo.py"], obj=Context()
    )
    parsed = json.loads(result.stdout)
    assert len(parsed) == 3


def test_check_specified_paths_and_staged(monkeypatch: MonkeyPatch) -> None:
    """Validates that check errors when --staged-only used with paths"""

    runner = CliRunner(mix_stderr=False)

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    try:
        runner.invoke(
            check,
            ["--staged-only", "init.js", "foo.py"],
            obj=Context(),
            catch_exceptions=False,
        )
        assert False
    except Exception:
        pass


def test_check_no_archive(monkeypatch: MonkeyPatch) -> None:
    """Validates that check operates without an archive file"""

    runner = CliRunner(mix_stderr=False)

    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))

    with util.mod_file(bento.constants.BASELINE_FILE_PATH):
        os.remove(bento.constants.BASELINE_FILE_PATH)
        result = runner.invoke(check, ["--formatter", "json"], obj=Context())
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
