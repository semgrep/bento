import os
from pathlib import Path
from typing import Collection, Set

from _pytest.monkeypatch import MonkeyPatch
from bento.context import Context
from bento.fignore import FileIgnore

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = (THIS_PATH / "..").absolute()
WALK_PATH = (BASE_PATH / "tests/integration/simple").relative_to(Path(os.getcwd()))


def __kept(ignores: Set[str]) -> Collection[str]:
    fi = FileIgnore(WALK_PATH, ignores)
    return {e.path for e in fi.entries() if e.survives}


def test_no_ignore() -> None:
    all_files = __kept(set())
    assert str(WALK_PATH / ".bento.yml") in all_files
    assert str(WALK_PATH / ".bento-whitelist.yml") in all_files


def test_ignore_any_dir() -> None:
    all_files = __kept({"dist/", "node_modules/", ".bento/"})
    assert str(WALK_PATH / "dist/init.min.js") not in all_files


def test_ignore_any_file() -> None:
    all_files = __kept({".bento.yml"})
    assert str(WALK_PATH / ".bento.yml") not in all_files


def test_ignore_root_file_exists() -> None:
    all_files = __kept({"/init.js"})
    assert str(WALK_PATH / "init.js") not in all_files


def test_ignore_root_file_not_exists() -> None:
    all_files = __kept({"/bar.js"})
    assert str(WALK_PATH / "dist" / "foo" / "bar.js") in all_files


def test_ignore_relative_file_exists() -> None:
    all_files = __kept({"./init.js"})
    assert str(WALK_PATH / "init.js") not in all_files


def test_ignore_relative_dot_file_exists() -> None:
    all_files = __kept({"./.bento/"})
    assert str(WALK_PATH / ".bento") not in all_files


def test_ignore_relative_file_not_exists() -> None:
    all_files = __kept({"./bar.js"})
    assert str(WALK_PATH / "dist" / "foo" / "bar.js") in all_files


def test_ignore_not_nested() -> None:
    all_files = __kept({"foo/bar.js", ".bento/"})
    assert str(WALK_PATH / "dist/foo/bar.js") in all_files


def test_ignore_nested_terminal_syntax() -> None:
    all_files = __kept({"foo/", ".bento/", "node_modules/"})
    assert str(WALK_PATH / "dist/foo/bar.js") not in all_files


def test_ignore_nested_double_start_syntax() -> None:
    all_files = __kept({"**/foo/", ".bento/"})
    assert str(WALK_PATH / "dist/foo/bar.js") not in all_files


def test_ignore_full_path() -> None:
    all_files = __kept({"dist/foo/bar.js"})
    assert str(WALK_PATH / "dist/foo/bar.js") not in all_files


def test_ignores_from_ignore_file(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(BASE_PATH)

    test_path = Path("tests") / "integration" / "simple"
    (test_path / ".bento").mkdir(exist_ok=True)
    (test_path / "node_modules").mkdir(exist_ok=True)

    ignores = Context(base_path=(BASE_PATH / "bento" / "configs"))._open_ignores()
    fi = FileIgnore(test_path, ignores)

    survivors = {e.path for e in fi.entries() if e.survives}
    assert survivors == {
        "tests/integration/simple/.eslintrc.yml",
        "tests/integration/simple/.bentoignore",
        "tests/integration/simple/.bento.yml",
        "tests/integration/simple/init.js",
        "tests/integration/simple/package-lock.json",
        "tests/integration/simple/package.json",
        "tests/integration/simple/bar.py",
        "tests/integration/simple/.bento-whitelist.yml",
        "tests/integration/simple/foo.py",
    }

    rejects = {e.path for e in fi.entries() if not e.survives}
    assert rejects == {
        "tests/integration/simple/.bento",
        "tests/integration/simple/dist",
        "tests/integration/simple/node_modules",
    }
