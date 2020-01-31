import time
from pathlib import Path
from typing import Collection, Iterable, List, Tuple

import click

import bento.constants
import bento.formatter
import bento.metrics
import bento.network
import bento.result
import bento.tool_runner
from bento.constants import IGNORE_FILE_NAME
from bento.context import Context
from bento.paths import run_context
from bento.tool import Tool
from bento.tool_runner import RunResults, RunStep
from bento.util import echo_warning


def orchestrate(
    context: Context, target_paths: List[Path], staged: bool, tools: Iterable[Tool]
) -> Tuple[Collection[RunResults], float]:
    baseline, elapsed = _calculate_baseline(context, target_paths, staged, tools)
    with run_context(context, target_paths, staged, RunStep.CHECK) as runner:
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
    context: Context, target_paths: List[Path], staged: bool, tools: Iterable[Tool]
) -> Tuple[bento.result.Baseline, float]:
    baseline: bento.result.Baseline = {}
    elapsed = 0.0

    if context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            baseline = bento.result.json_to_violation_hashes(json_file)

    if staged:
        head_baseline, elapsed = _calculate_head_comparison(
            context, target_paths, tools
        )
        for t in tools:
            tool_id = t.tool_id()
            if tool_id not in baseline:
                baseline[tool_id] = head_baseline.get(tool_id, set())
            else:
                baseline[tool_id].update(head_baseline.get(tool_id, set()))

    return baseline, elapsed


def _calculate_head_comparison(
    context: Context, target_paths: List[Path], tools: Iterable[Tool]
) -> Tuple[bento.result.Baseline, float]:
    """
    Calculates a baseline consisting of all findings from the branch head

    :param context: The cli context
    :param paths: Which paths are being checked
    :param tools: Which tools to check
    :return: The branch head baseline
    """
    with run_context(context, target_paths, True, RunStep.BASELINE) as runner:
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
