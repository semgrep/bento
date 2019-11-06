import sys
from typing import List, Set

import click

import bento.result
import bento.tool_runner
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_error, echo_success


@click.command()
@click.pass_obj
@with_metrics
def archive(context: Context) -> None:
    """
    Adds all current findings to the whitelist.
    """
    if not context.config_path.exists():
        echo_error("No Bento configuration found. Please run `bento init`.")
        sys.exit(3)
        return

    if context.baseline_file_path.exists():
        with context.baseline_file_path.open() as json_file:
            old_baseline = bento.result.yml_to_violation_hashes(json_file)
            old_hashes = {h for hh in old_baseline.values() for h in hh}
    else:
        old_hashes = set()

    new_baseline: List[str] = []
    tools = context.tools.values()

    all_findings = bento.tool_runner.Runner().parallel_results(tools, {}, None)
    n_found = 0
    n_existing = 0
    found_hashes: Set[str] = set()

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

    success_str = f"Rewrote the whitelist with {n_found} findings from {len(tools)} tools ({n_new} new, {n_existing} previously whitelisted)."
    if n_removed > 0:
        success_str += (
            f"\n  Also removed {n_removed} fixed findings from the whitelist."
        )
    success_str += f"\n  Please check '{context.pretty_path(context.baseline_file_path)}' in to source control."

    echo_success(success_str)
