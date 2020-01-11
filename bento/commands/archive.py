import sys
from pathlib import Path
from typing import Any, Dict, Set

import click

import bento.result
from bento.context import Context
from bento.decorators import with_metrics
from bento.paths import PathArgument, list_paths, run_context
from bento.result import VIOLATIONS_KEY
from bento.tool_runner import Comparison, RunStep
from bento.util import echo_error, echo_newline, echo_next_step


@click.command()
@click.option(
    "--staged",
    "--staged-only",
    help="Ignore diffs betweeen the filesystem and the git index.",
)
@click.argument("paths", nargs=-1, type=Path, autocompletion=list_paths)
@click.pass_obj
@with_metrics
def archive(
    context: Context, staged: bool, paths: PathArgument, show_bars: bool = True
) -> None:
    """
    Adds findings to the archive comparison point.
    """
    if not context.is_init:
        click.secho("Running Bento archive...\n" "", err=True)

    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)

    if context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            old_baseline = bento.result.load_baseline(json_file)
            old_hashes = {
                h
                for findings in old_baseline.values()
                for h in findings.get(VIOLATIONS_KEY, {}).keys()
            }
    else:
        old_baseline = {}
        old_hashes = set()

    new_baseline: Dict[str, Dict[str, Dict[str, Any]]] = {}
    tools = context.tools.values()

    with run_context(
        context,
        paths,
        comparison=Comparison.ROOT,
        staged=staged,
        run_step=RunStep.BASELINE,
        show_bars=show_bars,
    ) as runner:
        all_findings = runner.parallel_results(tools, {})

    n_found = 0
    n_existing = 0
    found_hashes: Set[str] = set()

    for tool_id, vv in all_findings:
        if isinstance(vv, Exception):
            raise vv
        n_found += len(vv)
        new_baseline[tool_id] = bento.result.dump_results(vv)
        if tool_id in old_baseline:
            new_baseline[tool_id][VIOLATIONS_KEY].update(
                old_baseline[tool_id][VIOLATIONS_KEY]
            )
        for v in vv:
            h = v.syntactic_identifier_str()
            found_hashes.add(h)
            if h in old_hashes:
                n_existing += 1

    n_new = n_found - n_existing

    context.baseline_file_path.parent.mkdir(exist_ok=True, parents=True)
    with context.baseline_file_path.open("w") as json_file:
        bento.result.write_tool_results(json_file, new_baseline)

    success_str = (
        f"{n_new} finding(s) were archived, and will be hidden in future Bento runs."
    )
    if n_existing > 0:
        success_str += f"\nBento also kept {n_existing} existing findings"

    click.echo(success_str, err=True)

    if not context.is_init:
        echo_newline()
        echo_next_step("To view archived results", "bento check --comparison root")
