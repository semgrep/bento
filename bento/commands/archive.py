import sys
from typing import List, Set

import click

import bento.result
import bento.tool_runner
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_error, echo_newline


@click.command()
@click.pass_obj
@with_metrics
def archive(context: Context, show_bars: bool = True) -> None:
    """
    Adds all current findings to the whitelist.
    """
    click.secho("Running Bento archive...\n" "", err=True)

    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)

    if context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            old_baseline = bento.result.yml_to_violation_hashes(json_file)
            old_hashes = {h for hh in old_baseline.values() for h in hh}
    else:
        old_hashes = set()

    new_baseline: List[str] = []
    tools = context.tools.values()

    all_findings = bento.tool_runner.Runner(show_bars=show_bars).parallel_results(
        tools, {}, None
    )
    n_found = 0
    n_existing = 0
    found_hashes: Set[str] = set()
    if show_bars:
        echo_newline()

    for tool_id, vv in all_findings:
        if isinstance(vv, Exception):
            raise vv
        n_found += len(vv)
        new_baseline += bento.result.tool_results_to_yml(tool_id, vv)
        for v in vv:
            h = v.syntactic_identifier_str()
            found_hashes.add(h)
            if h in old_hashes:
                n_existing += 1

    n_new = n_found - n_existing
    n_removed = len(old_hashes - found_hashes)

    context.baseline_file_path.parent.mkdir(exist_ok=True, parents=True)
    with context.baseline_file_path.open("w") as json_file:
        json_file.writelines(new_baseline)

    success_str = click.style(f"Project analyzed with {len(tools)} tool(s).", bold=True)
    success_str += f"\n{n_new} findings were added to your archive as a baseline."
    if n_existing > 0:
        success_str += f"\nBento also kept {n_existing} existing findings"
        if n_removed > 0:
            success_str += f" and removed {n_removed} fixed findings."
        else:
            success_str += "."
    elif n_removed > 0:
        success_str += f"\nBento also removed {n_removed} fixed findings."
    if not context.is_init:
        success_str += f"\nPlease check '{context.pretty_path(context.baseline_file_path)}' in to source control."

    click.echo(success_str, err=True)
