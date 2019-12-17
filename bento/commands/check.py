import logging
import os
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Collection, Dict, Iterable, Iterator, List, Optional, Tuple

import click
from pre_commit.git import get_staged_files
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import noop_context

import bento.constants
import bento.formatter
import bento.metrics
import bento.network
import bento.result
import bento.tool_runner
from bento.config import get_valid_tools, update_tool_run
from bento.context import Context
from bento.decorators import with_metrics
from bento.error import NodeError
from bento.tool import Tool
from bento.util import (
    AutocompleteSuggestions,
    echo_error,
    echo_newline,
    echo_next_step,
    echo_success,
    echo_warning,
)
from bento.violation import Violation

SHOW_ALL = "--show-all"
OVERRUN_PAGES = 3


def __get_ignores_for_tool(tool: str, config: Dict[str, Any]) -> List[str]:
    tool_config = config["tools"]
    tool_specific_config = tool_config[tool] or {}
    return tool_specific_config.get("ignore", [])


def __list_paths(ctx: Any, args: List[str], incomplete: str) -> AutocompleteSuggestions:
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


@contextmanager
def _process_paths(
    context: Context, paths: Optional[List[str]], staged_only: bool
) -> Iterator[Optional[List[str]]]:
    """
    Provides a with-expression within which a list of paths to be checked is provided

    This function operates in three different modes, depending on the value of
    the `paths` and `staged_only` variables:

    `paths` is truthy (a non-empty list), `staged_only` is false:
        The contents of `paths`, less any ignored paths, are passed to the with-expression

    `paths` is falsey, `staged_only` is true:
        All non-ignored files staged for git commit are passed to the with-expression

    `paths` is falsey, `staged_only` is false:
        None is passed to the with-expression (which causes check to run on the base path)

    In any of these modes, this function should be used as follows:

        with _process_paths(context, input_paths, staged_only) as processed_paths:
            ...

    :param context: The Bento command context
    :param paths: A list of paths to check, or None to indicate that check should operate
                  against the base path
    :param staged_only: Whether to use staged files as the list of paths
    :return: A Python with-expression
    :raises Exception: If staged_only is True and paths is truthy
    """
    git_stash = noop_context()

    if paths:
        if staged_only:
            raise Exception("--staged_only should not be used with explicit paths")
        paths = [
            str(
                context.base_path
                / os.path.relpath(os.path.abspath(p), context.base_path)
            )
            for p in paths
        ]
    elif staged_only:
        git_stash = staged_files_only(
            os.path.join(os.path.expanduser("~"), ".cache", "bento", "patches")
        )
        paths = get_staged_files()
    else:
        paths = None

    if paths is not None:
        paths = context.file_ignores.filter_paths(paths)

    with git_stash:
        yield paths


@click.command()
@click.option(
    "-f",
    "--formatter",
    type=click.Choice(bento.formatter.FORMATTERS.keys()),
    help="Which output format to use. Falls back to the formatter(s) configured in `.bento.yml`.",
    multiple=True,
)
@click.option(
    "--pager/--no-pager",
    help="Send long output through a pager. This should be disabled when used as an integration (e.g. with an editor).",
    default=True,
)
@click.option(
    SHOW_ALL,
    help="Show all findings, including those previously archived.",
    is_flag=True,
    default=False,
)
@click.option(
    "--staged-only",
    is_flag=True,
    help="Only runs over files staged in git. This should not be used with explicit paths.",
)
@click.option(
    "-t",
    "--tool",
    help="Specify a previously configured tool to run",
    autocompletion=get_valid_tools,
)
@click.argument("paths", nargs=-1, type=str, autocompletion=__list_paths)
@click.pass_obj
@with_metrics
def check(
    context: Context,
    formatter: Tuple[str, ...] = (),
    pager: bool = True,
    show_all: bool = False,
    staged_only: bool = False,
    tool: Optional[str] = None,
    paths: Optional[List[str]] = None,
) -> None:
    """
    Checks for new findings.

    Only findings not previously archived will be displayed (use --show-all
    to display archived findings).

    By default, 'bento check' will check the entire project. To run
    on one or more paths only, run:

      bento check path1 path2 ...
    """
    if tool and tool not in context.configured_tools:
        click.echo(
            f"{tool} has not been configured. Adding default configuration for tool to .bento.yml"
        )
        update_tool_run(context, tool, False)
        # Set configured_tools to None so that future calls will
        # update and include newly added tool
        context._configured_tools = None

    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)

    if not show_all and context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            baseline = bento.result.yml_to_violation_hashes(json_file)
    else:
        baseline = {}

    config = context.config
    if formatter:
        config["formatter"] = [{f: {}} for f in formatter]
    fmts = context.formatters
    findings_to_log: List[Any] = []

    click.echo("Running Bento checks...\n", err=True)

    with _process_paths(context, paths, staged_only) as processed_paths:
        if processed_paths is not None and len(processed_paths) == 0:
            echo_warning("All paths passed to `bento check` are ignored.")
            all_results: Collection[bento.tool_runner.RunResults] = []
            elapsed = 0.0

        else:
            before = time.time()
            runner = bento.tool_runner.Runner()
            tools: Iterable[Tool[Any]] = context.tools.values()

            if tool:
                tools = [context.configured_tools[tool]]

            all_results = runner.parallel_results(tools, baseline, processed_paths)
            elapsed = time.time() - before

    # Progress bars terminate on whitespace
    echo_newline()

    is_error = False

    n_all = 0
    n_all_filtered = 0
    filtered_findings: Dict[str, List[Violation]] = {}
    for tool_id, findings in all_results:
        if isinstance(findings, Exception):
            logging.error(findings)
            echo_error(f"Error while running {tool_id}: {findings}")
            if isinstance(findings, subprocess.CalledProcessError):
                click.secho(findings.stderr, err=True)
                click.secho(findings.stdout, err=True)
            if isinstance(findings, NodeError):
                echo_warning(
                    f"Node.js not found or version is not compatible with ESLint v6."
                )

            click.secho(
                f"""-------------------------------------------------------------------------------------------------
This may be due to a corrupted tool installation. You might be able to fix this issue by running:

  bento init --clean

You can also view full details of this error in `{bento.constants.DEFAULT_LOG_PATH}`.
-------------------------------------------------------------------------------------------------
""",
                err=True,
            )
            is_error = True
        elif isinstance(findings, list) and findings:
            findings_to_log += bento.metrics.violations_to_metrics(
                tool_id,
                context.timestamp,
                findings,
                __get_ignores_for_tool(tool_id, config),
            )
            filtered = [f for f in findings if not f.filtered]
            filtered_findings[tool_id] = filtered

            n_all += len(findings)
            n_filtered = len(filtered)
            n_all_filtered += n_filtered
            logging.debug(f"{tool_id}: {n_filtered} findings passed filter")

    def post_metrics() -> None:
        bento.network.post_metrics(findings_to_log, is_finding=True)

    stats_thread = threading.Thread(name="stats", target=post_metrics)
    stats_thread.start()

    dumped = [f.dump(filtered_findings) for f in fmts]
    context.start_user_timer()
    bento.util.less(dumped, pager=pager, overrun_pages=OVERRUN_PAGES)
    context.stop_user_timer()

    if n_all_filtered > 0:
        echo_warning(f"{n_all_filtered} finding(s) in {elapsed:.2f} s\n")
        if not context.is_init:
            echo_next_step("To suppress all findings", "bento archive")
    else:
        echo_success(f"0 findings in {elapsed:.2f} s\n")

    n_archived = n_all - n_all_filtered
    if n_archived > 0 and not show_all:
        echo_next_step(
            f"Not showing {n_archived} archived finding(s). To view",
            f"bento check {SHOW_ALL}",
        )

    if is_error:
        sys.exit(3)
    elif n_all_filtered > 0:
        sys.exit(2)
