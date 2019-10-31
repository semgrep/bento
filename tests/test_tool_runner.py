import os
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import bento.cli
import bento.context
import bento.result
import bento.tool_runner
from _pytest.monkeypatch import MonkeyPatch
from bento.violation import Violation

THIS_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.abspath(os.path.join(THIS_PATH, ".."))


def __len(it: Iterable[Any]) -> int:
    return sum(1 for _ in it)


def __violation_counts(violations: Iterable[Violation]) -> Tuple[int, int]:
    return (
        __len(filter(lambda v: not v.filtered, violations)),
        __len(filter(lambda v: v.filtered, violations)),
    )


def __count_simple_findings(
    archive: Dict[str, Set[str]], files: Optional[List[str]], monkeypatch: MonkeyPatch
) -> Dict[str, Tuple[int, int]]:
    """
    Runs __tool_parallel_results from the CLI

    Returns:
        (dict): Counts of (unfiltered, filtered) findings for each tool
    """
    monkeypatch.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))
    context = bento.context.Context()
    tools = context.tools.values()
    results = bento.tool_runner.Runner().parallel_results(
        tools, context.config, archive, files
    )
    return {tid: __violation_counts(vv) for tid, vv in results if isinstance(vv, list)}


def test_tool_parallel_results_no_archive_no_files(monkeypatch: MonkeyPatch) -> None:
    """Validates that tools are run in parallel and return proper finding counts (no archive, no passed files)"""
    counts = __count_simple_findings({}, None, monkeypatch)
    expectation = {"r2c.bandit": (2, 0), "r2c.eslint": (1, 0), "r2c.flake8": (2, 0)}

    assert counts == expectation


def test_tool_parallel_results_with_archive_no_files(monkeypatch: MonkeyPatch) -> None:
    """Validates that tools are run in parallel and return proper finding counts (archive, no passed files)"""
    with open(
        os.path.join(BASE_PATH, "tests/integration/simple/.bento-whitelist.yml")
    ) as file:
        archive = bento.result.yml_to_violation_hashes(file)
    counts = __count_simple_findings(archive, None, monkeypatch)

    expectation = {"r2c.bandit": (2, 0), "r2c.eslint": (1, 0), "r2c.flake8": (1, 1)}

    assert counts == expectation


def test_tool_parallel_results_no_archive_es_files(monkeypatch: MonkeyPatch) -> None:
    """Validates that tools are run in parallel and return proper finding counts (no archive, js files only)"""
    counts = __count_simple_findings({}, ["init.js"], monkeypatch)
    expectation = {"r2c.bandit": (0, 0), "r2c.eslint": (1, 0), "r2c.flake8": (0, 0)}

    assert counts == expectation


def test_tool_parallel_results_no_archive_py_files(monkeypatch: MonkeyPatch) -> None:
    """Validates that tools are run in parallel and return proper finding counts (no archive, single py file only)"""
    counts = __count_simple_findings({}, ["foo.py"], monkeypatch)
    expectation = {"r2c.bandit": (1, 0), "r2c.eslint": (0, 0), "r2c.flake8": (2, 0)}

    assert counts == expectation


def test_tool_parallel_results_archive_py_files(monkeypatch: MonkeyPatch) -> None:
    """Validates that tools are run in parallel and return proper finding counts (archive, passed files)"""
    with open(
        os.path.join(BASE_PATH, "tests/integration/simple/.bento-whitelist.yml")
    ) as file:
        archive = bento.result.yml_to_violation_hashes(file)
    counts = __count_simple_findings(archive, ["foo.py"], monkeypatch)
    expectation = {"r2c.bandit": (1, 0), "r2c.eslint": (0, 0), "r2c.flake8": (1, 1)}

    assert counts == expectation
