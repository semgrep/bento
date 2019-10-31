import logging
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import click
from pre_commit.git import get_staged_files
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import noop_context

import bento.formatter
import bento.network
import bento.result
import bento.tool_runner
from bento.context import Context
from bento.decorators import with_metrics
from bento.error import NodeError
from bento.util import AutocompleteSuggestions, echo_error, echo_success, echo_warning
from bento.violation import Violation


def __get_ignores_for_tool(tool: str, config: Dict[str, Any]) -> List[str]:
    tool_config = config["tools"]
    return tool_config[tool].get("ignore", [])


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
    "--formatter",
    type=click.Choice(bento.formatter.FORMATTERS.keys()),
    help="Which output format to use. Falls back to the config.",
    default=None,
)
@click.option(
    "--pager/--no-pager",
    help="Send long output through a pager. This should be disabled when used as an integration (e.g. with an editor).",
    default=True,
)
@click.option(
    "--staged-only",
    is_flag=True,
    help="Only runs over files staged in git. This should not be used with explicit paths",
)
@click.argument("paths", nargs=-1, type=str, autocompletion=__list_paths)
@click.pass_obj
@with_metrics
def check(
    context: Context,
    formatter: Optional[str] = None,
    pager: bool = True,
    staged_only: bool = False,
    paths: Optional[List[str]] = None,
) -> None:
    """
    Checks for new findings.

    Only findings not previously whitelisted will be displayed.

    By default, 'bento check' will check the entire project. To run
    on one or more paths only, run:

      bento check path1 path2 ...
    """

    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)

    if context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            baseline = bento.result.yml_to_violation_hashes(json_file)
    else:
        baseline = {}

    config = context.config
    if formatter:
        config["formatter"] = {formatter: {}}
    fmt = context.formatter
    findings_to_log: List[Any] = []

    def by_path(v: Violation) -> str:
        return v.path

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
        all_results = runner.parallel_results(tools, config, baseline, paths)
        elapsed = time.time() - before

    is_error = False

    collapsed_findings: List[Violation] = []
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

            click.echo("", err=True)
            is_error = True
        elif isinstance(findings, list) and findings:
            findings_to_log += bento.metrics.violations_to_metrics(
                tool_id, findings, __get_ignores_for_tool(tool_id, config)
            )
            collapsed_findings += [f for f in findings if not f.filtered]

    def post_metrics() -> None:
        bento.network.post_metrics(findings_to_log)

    stats_thread = threading.Thread(name="stats", target=post_metrics)
    stats_thread.start()

    if collapsed_findings:
        findings_by_path = sorted(collapsed_findings, key=by_path)
        for f in findings_by_path:
            logging.debug(f)
        bento.util.less(fmt.dump(findings_by_path), pager=pager, only_if_overrun=True)

    if collapsed_findings:
        echo_warning(f"{len(collapsed_findings)} findings in {elapsed:.2f} s\n")
        suppress_str = click.style("bento archive", fg="blue")
        click.echo(f"To suppress all findings run `{suppress_str}`.", err=True)
    else:
        echo_success(f"0 findings in {elapsed:.2f} s")

    if is_error:
        sys.exit(3)
    elif collapsed_findings:
        sys.exit(2)
