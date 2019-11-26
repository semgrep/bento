import logging
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

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
from bento.context import Context
from bento.decorators import with_metrics
from bento.error import NodeError
from bento.util import (
    AutocompleteSuggestions,
    Colors,
    echo_error,
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
@click.argument("paths", nargs=-1, type=str, autocompletion=__list_paths)
@click.pass_obj
@with_metrics
def check(
    context: Context,
    formatter: Tuple[str, ...] = (),
    pager: bool = True,
    show_all: bool = False,
    staged_only: bool = False,
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

    click.echo("Running Bento checks...", err=True)

    ctx = noop_context()
    if paths and len(paths) > 0:
        if staged_only:
            raise Exception("--staged_only should not be used with explicit paths")
    elif staged_only:
        ctx = staged_files_only(
            os.path.join(os.path.expanduser("~"), ".cache", "bento", "patches")
        )
        paths = get_staged_files()
    else:
        paths = None

    with ctx:
        before = time.time()
        runner = bento.tool_runner.Runner()
        tools = context.tools.values()
        all_results = runner.parallel_results(tools, baseline, paths)
        elapsed = time.time() - before

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

    if n_all_filtered > 0:
        dumped = [f.dump(filtered_findings) for f in fmts]
        context.start_user_timer()
        bento.util.less(dumped, pager=pager, overrun_pages=OVERRUN_PAGES)
        context.stop_user_timer()

        echo_warning(f"{n_all_filtered} finding(s) in {elapsed:.2f} s\n")
        suppress_str = click.style("bento archive", fg=Colors.STATUS)
        click.echo(f"◦ To suppress all findings run `{suppress_str}`.", err=True)
    else:
        echo_success(f"0 findings in {elapsed:.2f} s\n")

    n_archived = n_all - n_all_filtered
    if n_archived > 0 and not show_all:
        show_cmd = click.style(f"bento check {SHOW_ALL}", fg=Colors.STATUS)
        click.echo(
            f"◦ Not showing {n_archived} archived finding(s). To view, run `{show_cmd}`.",
            err=True,
        )

    if is_error:
        sys.exit(3)
    elif n_all_filtered > 0:
        sys.exit(2)
