import asyncio
import os
import shutil
import subprocess
import sys
import time
import traceback
from functools import partial
from multiprocessing import Lock, Pool
from pathlib import Path
from typing import Any, Callable, Dict, List, Set, Tuple, Union

import click
import yaml
from tqdm import tqdm

import bento.constants as constants
import bento.formatter as formatter
import bento.metrics
import bento.network as network
import bento.result as result
import bento.tool as tool
import bento.util
from bento.result import Baseline
from bento.util import echo_error, echo_success, echo_warning
from bento.violation import Violation

UPGRADE_WARNING_OUTPUT = f"""
╭─────────────────────────────────────────────╮
│  🎉 A new version of Bento is available 🎉  │
│  Try it out by running:                     │
│                                             │
│       {click.style("pip3 install --upgrade r2c-bento", fg="blue")}      │
│                                             │
╰─────────────────────────────────────────────╯
"""

TELEMETRY_PROMPT = f"""
│  Bento does not collect any source code or
│  send any source code outside of your
│  computer. Bento collects usage data to
│  help us understand how to improve the
│  product by aggregating anonymized
│  information about errors, slow operations,
│  feature utilization, and user preferences.
│  We do not and will not sell or share this
│  data to any third party.
│  For more inforamtion, see:
│  https://github.com/returntocorp/bento/blob/master/PRIVACY.md
"""

lock = Lock()
bars: List[tqdm]


def __tool_inventory() -> Dict[str, tool.Tool]:
    types = bento.util.package_subclasses(tool.Tool, "bento.extra")
    all_tools = {}
    for tt in types:
        ti = tt()
        ti.base_path = "."
        all_tools[ti.tool_id] = ti
    return all_tools


def __config() -> Dict[str, Any]:
    with open(constants.CONFIG_PATH) as yaml_file:
        return yaml.safe_load(yaml_file)


def __write_config(config: Dict[str, Any]) -> None:
    with open(constants.CONFIG_PATH, "w") as yaml_file:
        yaml.safe_dump(config, yaml_file)


def __install_config_if_not_exists() -> None:
    print(f"Creating default configuration at {constants.CONFIG_PATH}\n")
    if not os.path.exists(constants.CONFIG_PATH):
        shutil.copy(
            os.path.join(os.path.dirname(__file__), "configs/default.yml"),
            constants.CONFIG_PATH,
        )


def __tools(config: Dict[str, Any]) -> List[tool.Tool]:
    tools: List[tool.Tool] = []
    inventory = __tool_inventory()
    for tn in config["tools"].keys():
        ti = inventory.get(tn, None)
        if not ti:
            print(f"No tool named '{tn}' could be found")
            continue
        tools.append(ti)

    return tools


def __formatter(config: Dict[str, Any]) -> formatter.Formatter:
    if "formatter" not in config:
        return formatter.Stylish()
    else:
        f_class, cfg = next(iter(config["formatter"].items()))
        return formatter.for_name(f_class, cfg)


def __tool_findings(tool: tool.Tool, config: Dict[str, Any]) -> List[result.Violation]:
    tool_config = config["tools"].get(tool.tool_id, {})
    return tool.results(tool_config)


def __tool_filter(
    config: Dict[str, Any], baseline: Baseline, tool_and_index: Tuple[tool.Tool, int]
) -> Union[List[Violation], Exception]:
    """Runs a tool and filters out existing findings using baseline"""

    try:
        # print(f"{tool.tool_id} start")  # TODO: Move to debug
        # before = time.time_ns()
        tool, ix = tool_and_index
        tool.setup(config)
        with lock:
            bars[ix].update(1)
        # after_setup = time.time_ns()
        results = result.filter(tool.tool_id, __tool_findings(tool, config), baseline)
        with lock:
            bars[ix].update(2)
        # after = time.time_ns()
        # print(f"{tool.tool_id} completed in {((after - before) / 1e9):2f} s (setup in {((after_setup - before) / 1e9):2f} s)")  # TODO: Move to debug
        return results
    except Exception as e:
        traceback.print_exc()
        return e


def __update_ignores(tool: str, update_func: Callable[[Set[str]], None]) -> None:
    config = __config()
    tool_config = config["tools"]
    if tool not in tool_config:
        all_tools = ", ".join(f"'{k}'" for k in tool_config.keys())
        echo_error(f"No tool named '{tool}'. Configured tools are {all_tools}")
        sys.exit(3)

    ignores = set(tool_config[tool].get("ignore", []))
    update_func(ignores)

    tool_config[tool]["ignore"] = list(ignores)

    __write_config(config)


def get_ignores_for_tool(tool: str, config: Dict[str, Any]) -> List[str]:
    tool_config = config["tools"]
    return tool_config[tool].get("ignore", [])


def is_running_latest() -> bool:
    latest_version, _ = network.fetch_latest_version()
    if latest_version and get_version() < latest_version:
        return False
    return True


def get_version():
    """Get the current r2c-cli version based on __init__"""
    from bento import __version__

    return __version__


def _print_version(ctx, param, value):
    """Print the current r2c-cli version based on setuptools runtime"""
    if not value or ctx.resilient_parsing:
        return
    print(f"bento/{get_version()}")
    ctx.exit()


def is_running_supported_python3() -> bool:
    python_major_v = sys.version_info.major
    python_minor_v = sys.version_info.minor
    return python_major_v >= 3 and python_minor_v >= 6


@click.group()
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Show extra output, error messages, and exception stack traces with DEBUG filtering",
    default=False,
    hidden=True,
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show extra output, error messages, and exception stack traces with INFO filtering",
    default=False,
)
@click.option(
    "--version",
    is_flag=True,
    help="Show current version bento.",
    callback=_print_version,
    expose_value=False,
    is_eager=True,
)
def cli(debug, verbose):
    if not is_running_supported_python3():
        print("Please upgrade to python3.6 to run bento.")
    if not is_running_latest():
        click.echo(UPGRADE_WARNING_OUTPUT)


@cli.command()
def archive():
    """
    Adds all current findings to the whitelist.
    """
    if not os.path.exists(constants.CONFIG_PATH):
        echo_error("No Bento configuration found. Please run `bento init`.")
        return

    baseline: List[str] = []
    config = __config()
    total_findings = 0
    tools = __tools(config)
    for t in tools:
        try:
            findings = __tool_findings(t, config)
        except Exception as e:
            print(click.style(f"Exception while running {t.tool_id}: {e}", fg="red"))
            findings = []
        total_findings += len(findings)
        yml = result.tool_results_to_yml(t.tool_id, findings)
        baseline += yml

    os.makedirs(os.path.dirname(constants.BASELINE_FILE_PATH), exist_ok=True)
    with open(constants.BASELINE_FILE_PATH, "w") as json_file:
        json_file.writelines(baseline)

    echo_success(
        f"Rewrote the whitelist with {total_findings} findings from {len(tools)} tools."
    )

    asyncio.run(network.post_metrics(bento.metrics.command_metric("reset")))


@cli.command()
def init():
    """
    Installs all configured tools.

    Run again after changing tool list in .bento.yml
    """
    __install_config_if_not_exists()

    config = __config()

    tools = __tools(config)
    project_names = list(set(t.project_name for t in tools))
    if len(project_names) > 2:
        projects = f'{", ".join(project_names[:-2])}, and {project_names[-1]}'
    elif project_names:
        projects = " and ".join(project_names)
    else:
        print(click.style("bento can't identify this project", fg="red"))
        sys.exit(3)

    print(click.style(f"{TELEMETRY_PROMPT}\n", fg="yellow"))
    print(click.style(f"Detected project with {projects}\n", fg="blue"))

    for t in __tools(config):
        t.setup(config)

    Path(constants.BASELINE_FILE_PATH).touch()

    asyncio.run(network.post_metrics(bento.metrics.command_metric("setup")))


@cli.command()
@click.argument("tool", type=str, nargs=1)
@click.argument("check", type=str, nargs=1)
def disable(tool: str, check: str) -> None:
    """
    Disables a check.
    """

    def add(ignores: Set[str]) -> None:
        ignores.add(check)

    __update_ignores(tool, add)
    echo_success(f"'{check}' disabled for '{tool}'")


@cli.command()
@click.argument("tool", type=str, nargs=1)
@click.argument("check", type=str, nargs=1)
def enable(tool: str, check: str) -> None:
    """
    Enables a check.
    """

    def remove(ignores: Set[str]) -> None:
        if check in ignores:
            ignores.remove(check)

    __update_ignores(tool, remove)
    echo_success(f"'{check}' enabled for '{tool}'")


@cli.command()
def check():
    """
    Checks for new findings.

    Only findings not previously whitelisted will be displayed.
    """

    if not os.path.exists(constants.CONFIG_PATH):
        echo_error("No Bento configuration found. Please run `bento init`.")
        return

    if os.path.exists(constants.BASELINE_FILE_PATH):
        with open(constants.BASELINE_FILE_PATH) as json_file:
            baseline = result.yml_to_violation_hashes(json_file)
    else:
        baseline = {}

    config = __config()
    tools = __tools(config)
    fmt = __formatter(config)
    findings_to_log: List[Any] = []
    tools_and_indices = list(zip(tools, range(len(tools))))

    def by_path(v: Violation) -> str:
        return v.path

    # Progress bars can not be serialized, and therefore can not be used with
    # multiprocessing, except as a global variable
    def set_progress_bars(b: List[tqdm]) -> None:
        global bars
        bars = b

    click.echo("Running Bento checks...")
    bars = [
        tqdm(
            total=3,
            position=ix,
            desc=tool.tool_id,
            ncols=30,
            bar_format=click.style("  {desc}: |{bar}| {elapsed}", fg="blue"),
            leave=True,
        )
        for tool, ix in tools_and_indices
    ]

    before = time.time()
    with Pool(len(tools), initializer=set_progress_bars, initargs=(bars,)) as pool:
        # using partial to pass in multiple arguments to __tool_filter
        func = partial(__tool_filter, config, baseline)
        all_findings = enumerate(pool.map_async(func, tools_and_indices).get())
    elapsed = time.time() - before

    for b in bars:
        b.close()

    # click.echo("\x1b[1F")  # Resets line position afters bars close
    click.echo("")

    is_error = False

    notice = []
    collapsed_findings: List[Violation] = []
    for index, findings in all_findings:
        tool_id = tools[index].tool_id
        if isinstance(findings, Exception):
            notice.append(click.style(f"✘ Error while running {tool_id}:", fg="red"))
            notice.append(f"{findings}")
            if isinstance(findings, subprocess.CalledProcessError):
                notice.append(findings.stderr)
            notice.append("")
            is_error = True
        elif isinstance(findings, list) and findings:
            findings_to_log += bento.metrics.violations_to_metrics(
                tool_id, findings, get_ignores_for_tool(tool_id, config)
            )
            collapsed_findings += [f for f in findings if not f.filtered]

    if collapsed_findings:
        findings_by_path = sorted(collapsed_findings, key=by_path)
        notice += fmt.to_lines(findings_by_path)

    bento.util.less(notice, only_if_overrun=True)

    if collapsed_findings:
        echo_warning(f"{len(collapsed_findings)} findings in {elapsed:.2f} s")
        click.echo("")
        suppress_str = click.style("bento archive", fg="blue")
        click.echo(f"To suppress all findings run `{suppress_str}`.")

        asyncio.run(network.post_metrics(findings_to_log))

    else:
        echo_success(f"0 findings in {elapsed:.2f} s")

    asyncio.run(network.post_metrics(bento.metrics.command_metric("check")))

    if is_error:
        sys.exit(3)
    elif collapsed_findings:
        sys.exit(2)
