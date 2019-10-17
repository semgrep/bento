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

import bento.constants as constants
import bento.network
import bento.result
import bento.tool_runner
from bento.context import Context
from bento.error import NodeError
from bento.util import echo_error, echo_success, echo_warning
from bento.violation import Violation


def __get_ignores_for_tool(tool: str, config: Dict[str, Any]) -> List[str]:
    tool_config = config["tools"]
    return tool_config[tool].get("ignore", [])


@click.command()
@click.option(
    "--formatter",
    type=str,
    help="Which output format to use. Falls back to the config.",
    default=None,
)
@click.option(
    "--pager/--no-pager",
    help="Send long output through a pager. This should be disabled when used as an integration (e.g. with an editor).",
    default=True,
)
@click.option("--staged-only", is_flag=True, help="Only runs over files staged in git")
@click.pass_obj
def check(
    context: Context,
    formatter: Optional[str] = None,
    pager: bool = True,
    staged_only: bool = False,
) -> None:
    """
    Checks for new findings.

    Only findings not previously whitelisted will be displayed.
    """

    if not os.path.exists(constants.CONFIG_PATH):
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)
        return

    if os.path.exists(constants.BASELINE_FILE_PATH):
        with open(constants.BASELINE_FILE_PATH) as json_file:
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

    files = None
    if staged_only:
        ctx = staged_files_only(
            os.path.join(os.path.expanduser("~"), ".cache", "bento", "patches")
        )
        files = get_staged_files()
    else:
        ctx = noop_context()

    with ctx:
        before = time.time()
        runner = bento.tool_runner.Runner()
        tools = context.tools.values()
        all_results = runner.parallel_results(tools, config, baseline, files)
        elapsed = time.time() - before

    is_error = False

    collapsed_findings: List[Violation] = []
    for tool_id, findings in all_results:
        if isinstance(findings, Exception):
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
