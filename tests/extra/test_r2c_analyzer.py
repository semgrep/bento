import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

from semantic_version import Version

import docker
from bento.extra.r2c_analyzer import (
    REGISTRY,
    _ignore_files_factory,
    _should_pull_analyzer,
    prepull_analyzers,
    run_analyzer_on_local_code,
)

# These should be imported after r2c_analyzer because of monkeypatching
from r2c.lib.registry import RegistryData  # isort:skip
from r2c.lib.specified_analyzer import SpecifiedAnalyzer  # isort:skip
from r2c.lib.versioned_analyzer import AnalyzerName, VersionedAnalyzer  # isort:skip


def test_registry_parses() -> None:
    # Registry should parse without failures
    registry = RegistryData.from_json(REGISTRY)
    assert registry is not None


def test_should_pull() -> None:
    assert _should_pull_analyzer(
        SpecifiedAnalyzer(
            VersionedAnalyzer(AnalyzerName("doesnt/exist"), Version("9.1.1"))
        )
    )


def test_pull_analyzer() -> None:
    with patch.object(docker.client.ImageCollection, "pull", return_value=None) as spy:
        with patch(
            "bento.extra.r2c_analyzer._should_pull_analyzer", return_value=False
        ):
            # Should not pull
            prepull_analyzers("r2c/checked-return", Version("0.1.11"))
            assert spy.call_count == 0

        with patch("bento.extra.r2c_analyzer._should_pull_analyzer", return_value=True):
            # Should pull three times
            prepull_analyzers("r2c/checked-return", Version("0.1.11"))
            assert spy.call_count == 3

        with patch(
            "bento.extra.r2c_analyzer._should_pull_analyzer",
            side_effect=[False, True, False],
        ):
            # Should pull one more time
            prepull_analyzers("r2c/checked-return", Version("0.1.11"))
            assert spy.call_count == 4


def test_run_analyzer_on_local_code(tmp_path: Path) -> None:
    """
        Test running a local analyzer on code works
        Selected analyzer just copies a json file from input
        to output and we verify that output matches
    """
    file = tmp_path / "output.json"
    input_json = {
        "results": [
            {
                "check_id": "checked_return",
                "path": "./checkedreturn.js",
                "start": {"line": 25, "col": 3},
                "end": {"line": 25, "col": 15},
                "extra": {},
            }
        ]
    }

    file.write_text(json.dumps(input_json))
    output_json = run_analyzer_on_local_code(
        "r2c/testonly-cat-output-json", Version("1.0.2"), tmp_path, {str(file)}
    )
    assert input_json["results"] == output_json


def test_ignore_files_factory(tmp_path: Path) -> None:
    """
        Test that the function used for shutil.copytree ignore is correct

        Creates the following directory tree:
        - unignore_dir
            - file.txt
        - ignored_dir
            - file.txt
        - ignored_file.txt
        - unignored_file.txt

        And expects the following directory tree to be copied:
        - unignored_dir
            - file.txt
        - unignored_file.txt
    """
    source = tmp_path / "source"
    source.mkdir()
    # destination.mkdir()

    unignored_dir = source / "unignored_dir"
    unignored_dir.mkdir()
    ignored_dir = source / "ignored_dir"
    ignored_dir.mkdir()
    other_file = ignored_dir / "file.txt"
    other_file.touch()

    unignored_file = source / "unignored_file.txt"
    unignored_file.touch()
    ignored_file = source / "ignored_file.txt"
    ignored_file.touch()
    file_in_unignored_dir = unignored_dir / "file.txt"
    file_in_unignored_dir.touch()

    destination = tmp_path / "destination"
    # Copy tree using ignores
    expect_copy = {unignored_file, file_in_unignored_dir}
    shutil.copytree(
        source, destination, ignore=_ignore_files_factory({str(e) for e in expect_copy})
    )

    # Delete source and move back destination for easy comparion
    shutil.rmtree(source)
    shutil.copytree(destination, source)

    copied = set()
    for root, _, files in os.walk(source):
        for file in files:
            copied.add(Path(f"{root}/{file}"))

    assert expect_copy == copied


def test_ignore_files_factory_path(tmp_path: Path) -> None:
    """
        Test that the function used for shutil.copytree ignore is correct

        Creates the following directory tree:
        - unignore_dir
            - file.txt
        - ignored_dir
            - file.txt
        - ignored_file.txt
        - unignored_file.txt

        And expects the following directory tree to be copied:
        - unignored_dir
            - file.txt
    """
    source = tmp_path / "source"
    source.mkdir()
    # destination.mkdir()

    unignored_dir = source / "unignored_dir"
    unignored_dir.mkdir()
    ignored_dir = source / "ignored_dir"
    ignored_dir.mkdir()
    other_file = ignored_dir / "file.txt"
    other_file.touch()

    unignored_file = source / "unignored_file.txt"
    unignored_file.touch()
    ignored_file = source / "ignored_file.txt"
    ignored_file.touch()
    file_in_unignored_dir = unignored_dir / "file.txt"
    file_in_unignored_dir.touch()

    destination = tmp_path / "destination"
    # Copy tree using ignores
    expect_copy = {file_in_unignored_dir}
    shutil.copytree(
        source, destination, ignore=_ignore_files_factory({str(e) for e in expect_copy})
    )

    # Delete source and move back destination for easy comparion
    shutil.rmtree(source)
    shutil.copytree(destination, source)

    copied = set()
    for root, _, files in os.walk(source):
        for file in files:
            copied.add(Path(f"{root}/{file}"))

    assert expect_copy == copied
