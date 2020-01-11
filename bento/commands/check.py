import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Collection, Dict, Iterable, List, Optional, Tuple

import click

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
from bento.paths import PathArgument, list_paths, run_context
from bento.tool import Tool
from bento.tool_runner import Comparison, RunStep
from bento.util import echo_error, echo_next_step, echo_success, echo_warning
from bento.violation import Violation

OVERRUN_PAGES = 3
COMPARISONS = {
    Comparison.ROOT: "Shows all findings",
    Comparison.ARCHIVE: "Hides archived findings",
    Comparison.HEAD: "Hides all findings already in git",
}


def __get_ignores_for_tool(tool: str, config: Dict[str, Any]) -> List[str]:
    tool_config = config["tools"]
    tool_specific_config = tool_config[tool] or {}
    return tool_specific_config.get("ignore", [])


def _calculate_head_comparison(
    context: Context,
    paths: Optional[List[Path]],
    staged_only: bool,
    tools: Iterable[Tool],
) -> Tuple[bento.result.Baseline, float]:
    """
    Calculates a baseline consisting of all findings from the branch head

    :param context: The cli context
    :param paths: Which paths are being checked, or None for all paths
    :param staged_only: Whether to use staged files as the list of paths
    :param tools: Which tools to check
    :return: The branch head baseline
    """
    with run_context(
        context, paths, Comparison.HEAD, staged_only, RunStep.BASELINE
    ) as runner:
        if len(runner.paths) > 0:
            before = time.time()
            comparison_results = runner.parallel_results(tools, {}, keep_bars=False)
            baseline = {
                tool_id: {f.syntactic_identifier_str() for f in findings}
                for tool_id, findings in comparison_results
                if isinstance(findings, list)
            }
            elapsed = time.time() - before
            return baseline, elapsed
        else:
            return {}, 0.0


def _calculate_baseline(
    comparison: str,
    context: Context,
    paths: PathArgument,
    staged: bool,
    tools: Iterable[Tool],
) -> Tuple[bento.result.Baseline, float]:
    baseline: bento.result.Baseline = {}
    elapsed = 0.0

    if comparison != Comparison.ROOT and context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            baseline = bento.result.json_to_violation_hashes(json_file)

    if comparison == Comparison.HEAD:
        head_baseline, elapsed = _calculate_head_comparison(
            context, paths, staged, tools
        )
        baseline.update(head_baseline)

    return baseline, elapsed


@click.command()
@click.option(
    "-f",
    "--formatter",
    type=click.Choice(bento.formatter.FORMATTERS.keys()),
    help=f"Which output format to use. Falls back to the formatter(s) configured in `{bento.constants.CONFIG_FILE_NAME}`.",
    multiple=True,
)
@click.option(
    "--pager/--no-pager",
    help="Send long output through a pager. This should be disabled when used as an integration (e.g. with an editor).",
    default=True,
)
@click.option(
    "--comparison",
    help="Define a comparison point. Only new findings introduced since this point will be shown: Use 'root' to show "
    "all findings, 'archive' to show all unarchived findings, and 'head' to show only findings since the last "
    "git commit.",
    type=click.Choice(COMPARISONS.keys()),
    default=Comparison.HEAD,
)
@click.option(
    "--staged",
    "--staged-only",
    is_flag=True,
    help="Ignore diffs between the filesystem and the git index.",
)
@click.option(
    "-t",
    "--tool",
    help="Specify a previously configured tool to run",
    autocompletion=get_valid_tools,
)
@click.argument("paths", nargs=-1, type=Path, autocompletion=list_paths)
@click.pass_obj
@with_metrics
def check(
    context: Context,
    formatter: Tuple[str, ...] = (),
    pager: bool = True,
    comparison: str = Comparison.ARCHIVE,
    staged: bool = False,
    tool: Optional[str] = None,
    paths: PathArgument = None,
) -> None:
    """
    Checks for new findings.

    Only findings not previously archived will be displayed (use --show-all
    to display archived findings).

    By default, 'bento check' will check files modified since the last commit.

    To run on one or more paths only, run:

      bento check path1 path2 ...

    For example,

      bento check --comparison root .

    will check the whole project.
    """
    if tool and tool not in context.configured_tools:
        click.echo(
            f"{tool} has not been configured. Adding default configuration for tool to {bento.constants.CONFIG_FILE_NAME}"
        )
        update_tool_run(context, tool, False)
        # Set configured_tools to None so that future calls will
        # update and include newly added tool
        context._configured_tools = None

    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)

    config = context.config
    if formatter:
        config["formatter"] = [{f: {}} for f in formatter]
    fmts = context.formatters
    findings_to_log: List[Any] = []

    click.echo("Running Bento checks...\n", err=True)

    tools: Iterable[Tool[Any]] = context.tools.values()
    if tool:
        tools = [context.configured_tools[tool]]

    baseline, elapsed = _calculate_baseline(comparison, context, paths, staged, tools)

    with run_context(context, paths, comparison, staged, RunStep.CHECK) as runner:
        if len(runner.paths) == 0:
            echo_warning("All paths passed to `bento check` are ignored.")
            all_results: Collection[bento.tool_runner.RunResults] = []
            elapsed = 0.0
        else:
            before = time.time()
            all_results = runner.parallel_results(tools, baseline)
            elapsed += time.time() - before

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
    if n_archived > 0 and comparison == Comparison.ARCHIVE:
        echo_next_step(
            f"Not showing {n_archived} archived finding(s). To view",
            f"bento check --comparison {Comparison.ROOT}",
        )

    if staged and not context.autorun_is_blocking:
        return
    elif is_error:
        sys.exit(3)
    elif n_all_filtered > 0:
        sys.exit(2)
