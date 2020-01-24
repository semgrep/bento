import time
from pathlib import Path
from typing import Collection, Iterable, List, Optional, Tuple

import click

import bento.constants
import bento.formatter
import bento.metrics
import bento.network
import bento.result
import bento.tool_runner
from bento.constants import IGNORE_FILE_NAME
from bento.context import Context
from bento.paths import PathArgument, run_context
from bento.tool import Tool
from bento.tool_runner import Comparison, RunResults, RunStep
from bento.util import echo_warning


def orchestrate(
    context: Context, paths: PathArgument, staged: bool, tools: Iterable[Tool]
) -> Tuple[Collection[RunResults], float]:
    # TODO backwards compatible delta. Clean up here
    comparison = Comparison.HEAD if staged else Comparison.ARCHIVE

    baseline, elapsed = _calculate_baseline(comparison, context, paths, staged, tools)
    with run_context(context, paths, comparison, staged, RunStep.CHECK) as runner:
        if len(runner.paths) == 0:
            echo_warning(
                f"Nothing to check or archive. Please confirm that changes are staged and not excluded by `{IGNORE_FILE_NAME}`. To check all Git tracked files, use `--all`."
            )
            click.secho("", err=True)
            all_results: Collection[bento.tool_runner.RunResults] = []
            elapsed = 0.0
        else:
            before = time.time()
            all_results = runner.parallel_results(tools, baseline)
            elapsed += time.time() - before

    return all_results, elapsed


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
        for t in tools:
            tool_id = t.tool_id()
            if tool_id not in baseline:
                baseline[tool_id] = head_baseline.get(tool_id, set())
            else:
                baseline[tool_id].update(head_baseline.get(tool_id, set()))

    return baseline, elapsed


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
