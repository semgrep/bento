import sys
from typing import Dict, Set

import click

import bento.result
import bento.tool_runner
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_error, echo_newline, echo_next_step


@click.command()
@click.pass_obj
@with_metrics
def archive(context: Context, show_bars: bool = True) -> None:
    """
    Adds all current findings to the whitelist.
    """
    if not context.is_init:
        click.secho("Running Bento archive...\n" "", err=True)

    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)

    if context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            old_baseline = bento.result.json_to_violation_hashes(json_file)
            old_hashes = {h for hh in old_baseline.values() for h in hh}
    else:
        old_hashes = set()

    new_baseline: Dict[str, bento.result.ToolResults] = {}
    tools = context.tools.values()

    all_findings = bento.tool_runner.Runner(show_bars=show_bars).parallel_results(
        tools, {}, None
    )
    n_found = 0
    n_existing = 0
    found_hashes: Set[str] = set()

    for tool_id, vv in all_findings:
        if isinstance(vv, Exception):
            raise vv
        n_found += len(vv)
        new_baseline[tool_id] = bento.result.dump_results(vv)
        for v in vv:
            h = v.syntactic_identifier_str()
            found_hashes.add(h)
            if h in old_hashes:
                n_existing += 1

    n_new = n_found - n_existing
    n_removed = len(old_hashes - found_hashes)

    context.baseline_file_path.parent.mkdir(exist_ok=True, parents=True)
    with context.baseline_file_path.open("w") as json_file:
        bento.result.write_tool_results(json_file, new_baseline)

    success_str = click.style(f"Project analyzed with {len(tools)} tool(s).", bold=True)
    success_str += (
        f"\n{n_new} finding(s) were archived, and will be hidden in future Bento runs."
    )
    if n_existing > 0:
        success_str += f"\nBento also kept {n_existing} existing findings"
        if n_removed > 0:
            success_str += f" and removed {n_removed} fixed findings."
        else:
            success_str += "."
    elif n_removed > 0:
        success_str += f"\nBento also removed {n_removed} fixed findings."

    click.echo(success_str, err=True)

    if not context.is_init:
        echo_newline()
        echo_next_step("To view archived results", "bento check --show-all")
        click.echo(
            f"\nPlease check '{context.pretty_path(context.baseline_file_path)}' in to source control.",
            err=True,
        )
