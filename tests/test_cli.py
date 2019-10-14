import os
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml

import bento.cli
import bento.extra.eslint
import bento.result
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
    archive: Dict[str, Set[str]], files: Optional[List[str]]
) -> Dict[str, Tuple[int, int]]:
    """
    Runs __tool_parallel_results from the CLI

    Returns:
        (dict): Counts of (unfiltered, filtered) findings for each tool
    """
    with open(os.path.join(BASE_PATH, "tests/integration/simple/.bento.yml")) as file:
        config = yaml.safe_load(file)
    current_path = os.getcwd()
    try:
        os.chdir(os.path.join(BASE_PATH, "tests/integration/simple"))
        results = bento.cli.__tool_parallel_results(config, archive, files)
        return dict(
            (tid, __violation_counts(vv)) for tid, vv in results if isinstance(vv, list)
        )
    finally:
        os.chdir(current_path)


def test_tool_from_config_found() -> None:
    """Validates that existing tools are parsed from the config file"""
    config: Dict[str, Any] = {"tools": {"r2c.eslint": {"ignore": []}}}
    tools = bento.cli.__tools(config)
    assert len(tools) == 1
    assert tools[0].tool_id() == "r2c.eslint"


def test_tool_from_config_missing() -> None:
    """Validates that non-existant tools are silently ignored in the config file"""
    config: Dict[str, Any] = {"tools": {"r2c.not_a_thing": {"ignore": []}}}
    assert len(bento.cli.__tools(config)) == 0


def test_tool_parallel_results_no_archive_no_files() -> None:
    """Validates that tools are run in parallel and return proper finding counts (no archive, no passed files)"""
    counts = __count_simple_findings({}, None)
    expectation = {"r2c.bandit": (2, 0), "r2c.eslint": (1, 0), "r2c.flake8": (2, 0)}

    assert counts == expectation


def test_tool_parallel_results_with_archive_no_files() -> None:
    """Validates that tools are run in parallel and return proper finding counts (archive, no passed files)"""
    with open(
        os.path.join(BASE_PATH, "tests/integration/simple/.bento-whitelist.yml")
    ) as file:
        archive = bento.result.yml_to_violation_hashes(file)
    counts = __count_simple_findings(archive, None)

    expectation = {"r2c.bandit": (2, 0), "r2c.eslint": (1, 0), "r2c.flake8": (1, 1)}

    assert counts == expectation


def test_tool_parallel_results_no_archive_es_files() -> None:
    """Validates that tools are run in parallel and return proper finding counts (no archive, js files only)"""
    counts = __count_simple_findings({}, ["init.js"])
    expectation = {"r2c.bandit": (0, 0), "r2c.eslint": (1, 0), "r2c.flake8": (0, 0)}

    assert counts == expectation


def test_tool_parallel_results_no_archive_py_files() -> None:
    """Validates that tools are run in parallel and return proper finding counts (no archive, single py file only)"""
    counts = __count_simple_findings({}, ["foo.py"])
    expectation = {"r2c.bandit": (1, 0), "r2c.eslint": (0, 0), "r2c.flake8": (2, 0)}

    assert counts == expectation


def test_tool_parallel_results_archive_py_files() -> None:
    """Validates that tools are run in parallel and return proper finding counts (archive, passed files)"""
    with open(
        os.path.join(BASE_PATH, "tests/integration/simple/.bento-whitelist.yml")
    ) as file:
        archive = bento.result.yml_to_violation_hashes(file)
    counts = __count_simple_findings(archive, ["foo.py"])
    expectation = {"r2c.bandit": (1, 0), "r2c.eslint": (0, 0), "r2c.flake8": (1, 1)}

    assert counts == expectation
