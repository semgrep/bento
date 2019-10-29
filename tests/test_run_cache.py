import time
from pathlib import Path
from typing import List, Tuple

from _pytest.monkeypatch import MonkeyPatch
from bento.run_cache import RunCache

TOOL_ID = "tool_name_here"
TOOL_OUTPUT = "this is tool output"


def __ensure_ubuntu_mtime_change() -> None:
    """
    On Ubuntu, file mtimes are not updated if a small enough time has passed.

    To ensure mtime change, sleep at least 10 ms.
    """
    time.sleep(1e-2)


def __setup_test_dir(tmp_path: Path) -> Tuple[str, List[str], Path]:
    paths = [str(tmp_path)]
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    file = subdir / "hello.txt"
    file.touch()
    return RunCache._modified_hash(paths), paths, file


def test_modified_hash_no_changes(tmp_path: Path) -> None:
    """modified_hash should not change if no files change"""

    hsh, paths, _ = __setup_test_dir(tmp_path)
    __ensure_ubuntu_mtime_change()

    assert hsh == RunCache._modified_hash(paths)


def test_modified_hash_new_file_subdir(tmp_path: Path) -> None:
    """modified_hash should change if a new file in subdir is added"""
    paths = [str(tmp_path)]
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    hsh = RunCache._modified_hash(paths)
    sub_hash = RunCache._modified_hash([str(subdir)])

    (subdir / "hello.txt").touch()

    assert hsh != RunCache._modified_hash(paths)
    assert sub_hash != RunCache._modified_hash([str(subdir)])


def test_modified_hash_touch(tmp_path: Path) -> None:
    """modified_hash should change if a file is modified"""

    hsh, paths, file = __setup_test_dir(tmp_path)
    __ensure_ubuntu_mtime_change()
    file.touch()

    assert hsh != RunCache._modified_hash(paths)


def test_modified_hash_remove(tmp_path: Path) -> None:
    """modified_hash should change if a file is removed"""

    hsh, paths, file = __setup_test_dir(tmp_path)
    file.unlink()

    assert hsh != RunCache._modified_hash(paths)


def test_modified_hash_ignore(tmp_path: Path) -> None:
    """modifed_hash should ignore changes in exclude dirs"""
    paths = [str(tmp_path)]
    subdir = tmp_path / "node_modules"
    subdir.mkdir()

    hsh = RunCache._modified_hash(paths)

    (subdir / "hello.txt").touch()

    assert hsh == RunCache._modified_hash(paths)


def test_get(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _, paths, file = __setup_test_dir(tmp_path)

    monkeypatch.chdir(paths[0])

    # Check cache is retrievable
    assert RunCache.get(TOOL_ID, ["."]) is None
    RunCache.put(TOOL_ID, ["."], TOOL_OUTPUT)
    assert RunCache.get(TOOL_ID, ["."]) == TOOL_OUTPUT

    # Check that modifying file invalidates cache
    __ensure_ubuntu_mtime_change()
    file.touch()

    assert RunCache.get(TOOL_ID, ["."]) is None
