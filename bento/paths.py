import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Optional

from pre_commit.git import zsplit
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import cmd_output, noop_context

import bento.git
from bento.context import Context
from bento.tool_runner import Comparison, Runner, RunStep
from bento.util import AutocompleteSuggestions

PATCH_CACHE = str(Path.home() / ".cache" / "bento" / "patches")


PathArgument = Optional[List[Path]]


def _diffed_paths(context: Context, staged_only: bool) -> List[Path]:
    repo = bento.git.repo()
    if not repo:
        return []
    cmd = [
        "git",
        "diff",
        "--name-only",
        "--no-ext-diff",
        "-z",
        # Everything except for D
        "--diff-filter=ACMRTUXB",
        "--relative",
        "--staged" if staged_only else "HEAD",
        "--",
        str(context.base_path),
    ]
    result = repo.git.execute(cmd)
    str_paths = zsplit(result)
    return [Path(p) for p in str_paths]


@contextmanager
def head_context() -> Iterator[None]:
    repo = bento.git.repo()

    if not repo:
        yield

    else:
        with staged_files_only(PATCH_CACHE):
            tree = cmd_output("git", "write-tree")[1].strip()
            try:
                cmd_output("git", "reset", "--hard")
                yield
            finally:
                cmd_output("git", "checkout", tree, "--", ".")


@contextmanager
def run_context(
    context: Context,
    input_paths: PathArgument,
    comparison: str,
    staged: bool,
    run_step: RunStep,
    show_bars: bool = True,
) -> Iterator[Runner]:
    """
    Provides a context within which to run tools.

    This context obeys the following behaviors:

        Filesystem modifications:
            comparison is head, running baseline - files are reset to head git index
            staged is true - file diffs are removed
            otherwise - no changes

        Paths to be checked:
            explicit paths - these paths are used
            staged is true - only paths with staged changes are used
            otherwise - only paths with diffs vs the head git index are used

    :param context: The Bento command context
    :param input_paths: A list of paths to check, or None to indicate that check should operate
                  against the base path
    :param comparison: Which archive comparison is in use
    :param staged: Whether to use remove file diffs
    :param run_step: Which run step is in use (baseline if tool is determining baseline, check if tool is finding new results)
    :param show_bars: If true, attempts to configure Runner to display progress bars (these may not be displayed if not supported by environment)
    :return: A Python with-expression, which is passed a Runner object
    :raises Exception: If comparison is not HEAD and run_step is not CHECK
    """
    is_explicit_paths = input_paths is not None and len(input_paths) > 0

    if comparison == Comparison.HEAD and run_step == RunStep.BASELINE:
        stash_context = head_context()
    elif staged:
        stash_context = staged_files_only(PATCH_CACHE)
    else:
        stash_context = noop_context()

    if comparison == Comparison.HEAD and run_step == RunStep.CHECK:
        use_cache = False
        skip_setup = True
    else:
        use_cache = True
        skip_setup = False

    if is_explicit_paths:
        paths = [
            context.base_path / p.resolve().absolute().relative_to(context.base_path)
            for p in (input_paths or [])
        ]
    else:
        paths = _diffed_paths(context, staged_only=staged)

    paths = context.file_ignores.filter_paths(paths)

    with stash_context:
        yield Runner(
            paths=paths, use_cache=use_cache, skip_setup=skip_setup, show_bars=show_bars
        )


def list_paths(ctx: Any, args: List[str], incomplete: str) -> AutocompleteSuggestions:
    """
    Lists paths when tab autocompletion is used on a path argument.

    Note that click always adds a space at the end of a suggestion, so repeated tabbing
    can not be used to fill a path. :(

    :param ctx: Unused
    :param args: Unused
    :param incomplete: Any partial completion currently under the cursor
    :return: A list of completion suggestions
    """
    # Cases for "incomplete" variable:
    #   - '': Search '.', no filtering
    #   - 'part_of_file': Search '.', filter
    #   - 'path/to/dir/': Search 'path/to/dir', no filter
    #   - 'path/to/dir/part_of_file': Search 'path/to/dir', filter
    dir_root = os.path.dirname(incomplete)
    path_stub = incomplete[len(dir_root) :]
    if path_stub.startswith("/"):
        path_stub = path_stub[1:]
    if dir_root == "":
        dir_to_list = "."
    else:
        dir_to_list = dir_root
    return [
        os.path.join(dir_root, p)
        for p in os.listdir(dir_to_list)
        if not path_stub or p.startswith(path_stub)
    ]
