import time
from typing import Any

from _pytest.monkeypatch import MonkeyPatch
from bento.run_cache import RunCache

TOOL_ID = "tool_name_here"
TOOL_OUTPUT = "this is tool output"


def test_modified_since_new_file(tmpdir: Any) -> None:
    """modified_since should return true if a new file is added"""
    subdir = tmpdir.mkdir("subdir")

    start = time.time()

    # For some reason on circleci time returned by time.time()
    # is slightly delayed from system mtime of file written below
    # adding some artificial delay
    time.sleep(0.01)

    subdir.join("hello.txt").write("potato")
    end = time.time()

    assert RunCache._modified_since([tmpdir], [tmpdir], start)
    assert not RunCache._modified_since([tmpdir], [tmpdir], end)


def test_modified_since_touch(tmpdir: Any) -> None:
    """modified_since should return true if a file is touched"""
    subdir = tmpdir.mkdir("subdir")

    start = time.time()

    # For some reason on circleci time returned by time.time()
    # is slightly delayed from system mtime of file written below
    # adding some artificial delay
    time.sleep(0.01)

    subdir.join("hello.txt").write("potato")
    end = time.time()

    # For some reason on circleci time returned by time.time()
    # is slightly delayed from system mtime of file written below
    # adding some artificial delay
    time.sleep(0.01)

    subdir.join("hello.txt").write("new")

    assert RunCache._modified_since([tmpdir], [tmpdir], start)
    assert RunCache._modified_since([tmpdir], [tmpdir], end)


def test_modified_since_ignore(tmpdir: Any) -> None:
    """modifed_since should ignore changes in exclude dirs"""
    subdir = tmpdir.mkdir("node_modules")

    start = time.time()

    # For some reason on circleci time returned by time.time()
    # is slightly delayed from system mtime of file written below
    # adding some artificial delay
    time.sleep(0.01)
    subdir.join("hello.txt").write("potato")

    end = time.time()

    # For some reason on circleci time returned by time.time()
    # is slightly delayed from system mtime of file written below
    # adding some artificial delay
    time.sleep(0.01)

    subdir.join("hello.txt").write("new")

    assert not RunCache._modified_since([tmpdir], [tmpdir], start)
    assert not RunCache._modified_since([tmpdir], [tmpdir], end)


def test_get(tmpdir: Any, monkeypatch: MonkeyPatch) -> None:
    subdir = tmpdir.mkdir("subdir")
    subdir.join("hello.py").write("potato")

    monkeypatch.chdir(tmpdir)

    # Check cache is retrivable
    assert RunCache.get(TOOL_ID, ["."]) is None
    RunCache.put(TOOL_ID, ["."], TOOL_OUTPUT)
    assert RunCache.get(TOOL_ID, ["."]) == TOOL_OUTPUT

    # Check that modifying file invalidates cache

    # For some reason on circleci time returned by time.time()
    # is slightly delayed from system mtime of file written below
    # adding some artificial delay
    time.sleep(0.01)

    subdir.join("hello.py").write("potato")
    assert RunCache.get(TOOL_ID, ["."]) is None
