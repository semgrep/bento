import os
import shutil
import stat
import subprocess
import sys
import threading
import time
import traceback
from functools import partial
from multiprocessing import Lock, Pool
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

import click
import git
import requests
import yaml
from pre_commit.git import get_staged_files
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import noop_context
from semantic_version import Version
from tqdm import tqdm

import bento.constants as constants
import bento.extra
import bento.formatter as formatter
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

TERMS_OF_SERVICE_MESSAGE = f"""│ Bento does not collect any source code or send any source code outside of your
│ computer. Bento collects usage data to help us understand how to improve the
│ product by aggregating anonymized information about errors, slow operations,
│ feature utilization, and user preferences. We do not and will not sell or share
│ this data to any third party. For more information, see:
│ https://github.com/returntocorp/bento/blob/master/PRIVACY.md
"""

TERMS_OF_SERVICE_ERROR = f"""
Bento did NOT install. Bento beta users must agree to the terms of service to continue. Please reach out to us at support@r2c.dev with questions or concerns.
"""

MAX_BAR_VALUE = 30
BAR_UPDATE_INTERVAL = 0.1

lock = Lock()
bars: List[tqdm]


def __tool_inventory() -> Dict[str, tool.Tool]:
    all_tools = {}
    types = bento.util.package_subclasses(tool.Tool, "bento.extra")
    for tt in types:
        if not tt.__abstractmethods__:
            # Skip abstract tool classes
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
    if not os.path.exists(constants.CONFIG_PATH):
        click.echo(f"Creating default configuration at {constants.CONFIG_PATH}\n")
        with (
            open(os.path.join(os.path.dirname(__file__), "configs/default.yml"))
        ) as template:
            yml = yaml.safe_load(template)
        for tid, t in __tool_inventory().items():
            if not t.matches_project():
                del yml["tools"][tid]
        with (open(constants.CONFIG_PATH, "w")) as config_file:
            yaml.safe_dump(yml, stream=config_file)


def __tools(config: Dict[str, Any]) -> List[tool.Tool]:
    tools: List[tool.Tool] = []
    inventory = __tool_inventory()
    for tn in config["tools"].keys():
        ti = inventory.get(tn, None)
        if not ti:
            echo_error(f"No tool named '{tn}' could be found")
            continue
        tools.append(ti)

    return tools


def __formatter(config: Dict[str, Any]) -> formatter.Formatter:
    if "formatter" not in config:
        return formatter.Stylish()
    else:
        f_class, cfg = next(iter(config["formatter"].items()))
        return formatter.for_name(f_class, cfg)


def __tool_findings(
    tool: tool.Tool, config: Dict[str, Any], paths: Optional[Iterable[str]] = None
) -> List[result.Violation]:
    tool_config = config["tools"].get(tool.tool_id, {})
    return tool.results(tool_config, paths)


def __tool_filter(
    config: Dict[str, Any],
    baseline: Baseline,
    paths: Optional[Iterable[str]],
    tool_and_index: Tuple[tool.Tool, int],
) -> Union[List[Violation], Exception]:
    """Runs a tool and filters out existing findings using baseline"""

    min_bar_value = int(MAX_BAR_VALUE / 5)
    run = True

    def update_bars() -> None:
        bar_value = min_bar_value
        keep_going = True
        while keep_going:
            with lock:
                keep_going = run
                if bar_value < MAX_BAR_VALUE - 1:
                    bar_value += 1
                    bars[ix].update(1)
                else:
                    bar_value = min_bar_value
                    bars[ix].update(min_bar_value - MAX_BAR_VALUE + 1)
            time.sleep(BAR_UPDATE_INTERVAL)
        with lock:
            bars[ix].update(MAX_BAR_VALUE - bar_value)

    try:
        # print(f"{tool.tool_id} start")  # TODO: Move to debug
        # before = time.time_ns()
        tool, ix = tool_and_index
        with lock:
            bars[ix].set_postfix_str("🍜")
        tool.setup(config)
        with lock:
            bars[ix].update(min_bar_value)
            bars[ix].set_postfix_str("🍤")
        # after_setup = time.time_ns()
        th = threading.Thread(name=f"update_{ix}", target=update_bars)
        th.start()
        results = result.filter(
            tool.tool_id, __tool_findings(tool, config, paths), baseline
        )
        with lock:
            run = False
        th.join()
        with lock:
            bars[ix].set_postfix_str("🍱")
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
    click.echo(f"bento/{get_version()}")
    ctx.exit()


def __post_email_to_mailchimp(email: str) -> bool:
    r = requests.post(
        "http://waitlist.r2c.dev/subscribe/cli-user", json={"email": email}, timeout=5
    )

    status = r.status_code == requests.codes.ok
    network.post_metrics(
        [
            {
                "message": "Tried adding user to Bento waitlist",
                "user-email": email,
                "mailchimp_response": r.status_code,
                "success": status,
            }
        ]
    )
    return status


def is_running_supported_python3() -> bool:
    python_major_v = sys.version_info.major
    python_minor_v = sys.version_info.minor
    return python_major_v >= 3 and python_minor_v >= 6


def has_completed_registration() -> bool:
    if not os.path.exists(constants.GLOBAL_CONFIG_PATH):
        return False

    with open(constants.GLOBAL_CONFIG_PATH) as yaml_file:
        global_config = yaml.safe_load(yaml_file)

    if constants.TERMS_OF_SERVICE_KEY not in global_config:
        return False

    # We care that there is a version of the terms of service a user has agreed to,
    # taking a "good enough" approach with no validation that it's a version that
    # actually exists.

    tos_version = global_config[constants.TERMS_OF_SERVICE_KEY]
    # If Version throws an exception, then string is not a valid semver
    try:
        Version(version_string=tos_version)
    except Exception:
        raise ValueError(
            f"Invalid semver for `{constants.TERMS_OF_SERVICE_KEY}` in {constants.GLOBAL_CONFIG_PATH}: {tos_version}. Deleting the key/value and re-running Bento should resolve the issue."
        )

    return True


def register_user() -> bool:
    global_config = {}

    bolded_welcome = click.style(f"Welcome to Bento!", bold=True)
    click.echo(
        f"{bolded_welcome} You're about to get a powerful suite of tailored tools.\n"
    )
    click.echo(
        f"To get started for the first time, please review our terms of service:\n\n{TERMS_OF_SERVICE_MESSAGE}"
    )

    agreed_terms_of_service = click.confirm(
        "Do you agree to Bento's terms of service and privacy policy?", default=True
    )
    if agreed_terms_of_service:
        global_config[
            constants.TERMS_OF_SERVICE_KEY
        ] = constants.TERMS_OF_SERVICE_VERSION
    else:
        bento.util.echo_error(TERMS_OF_SERVICE_ERROR)
        return False

    subscribe_to_email = click.confirm(
        "For the Bento beta, may we contact you infrequently via email to ask for your feedback and let you know about updates? You can unsubscribe at any time.",
        default=True,
    )

    if subscribe_to_email:
        email = click.prompt(
            "Email", type=str, default=bento.metrics.__get_git_user_email()
        )
        global_config["email"] = email
        r = __post_email_to_mailchimp(email)
        if not r:
            echo_warning(
                "\nWe were unable to subscribe you to the Bento mailing list, but will continue with installation. Please shoot us a note via support@r2c.dev to debug."
            )

    os.makedirs(constants.GLOBAL_CONFIG_DIR, exist_ok=True)
    with open(constants.GLOBAL_CONFIG_PATH, "w+") as yaml_file:
        yaml.safe_dump(global_config, yaml_file)

    click.echo(f"\nCreated user configs at {constants.GLOBAL_CONFIG_PATH}.")

    return True


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
@click.option(
    "--agree",
    is_flag=True,
    help="Automatically agree to terms of service.",
    default=False,
)
def cli(debug, verbose, agree):
    if not is_running_supported_python3():
        echo_error(
            "Bento requires Python 3.6+. Please ensure you have Python 3.6+ and installed Bento via `pip3 install r2c-bento`."
        )
        sys.exit(3)
    if not agree and not has_completed_registration():
        registered = register_user()
        if not registered:
            # Terminate with non-zero error
            sys.exit(3)
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
            bento.util.echo_error(f"Exception while running {t.tool_id}: {e}")
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

    network.post_metrics(bento.metrics.command_metric("reset"))


@cli.command()
def init():
    """
    Autodetects and installs tools.

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
        echo_error("Bento can't identify this project.")
        sys.exit(3)

    click.secho(f"Detected project with {projects}\n", fg="blue")

    for t in __tools(config):
        t.setup(config)

    Path(constants.BASELINE_FILE_PATH).touch()

    network.post_metrics(bento.metrics.command_metric("setup"))


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
def check(
    formatter: Optional[str] = None, pager: bool = True, staged_only: bool = False
) -> None:
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
    if formatter:
        config["formatter"] = {formatter: {}}
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

    click.echo("Running Bento checks...", err=True)
    bars = [
        tqdm(
            total=MAX_BAR_VALUE,
            position=ix,
            mininterval=BAR_UPDATE_INTERVAL,
            desc=tool.tool_id,
            ncols=40,
            bar_format=click.style("  {desc}: |{bar}| {elapsed}{postfix}", fg="blue"),
            leave=False,
        )
        for tool, ix in tools_and_indices
    ]

    files = None
    if staged_only:
        ctx = staged_files_only(".")
        files = get_staged_files()
    else:
        ctx = noop_context()
    with ctx:
        before = time.time()
        with Pool(len(tools), initializer=set_progress_bars, initargs=(bars,)) as pool:
            # using partial to pass in multiple arguments to __tool_filter
            func = partial(__tool_filter, config, baseline, files)
            all_findings = enumerate(pool.map_async(func, tools_and_indices).get())
        elapsed = time.time() - before

    # click.echo("\x1b[1F")  # Resets line position afters bars close
    for b in bars:
        click.echo("", err=True)
    for b in bars:
        b.close()

    click.echo("", err=True)

    is_error = False

    def post_metrics():
        network.post_metrics(findings_to_log)

    stats_thread = threading.Thread(name="stats", daemon=True, target=post_metrics)
    stats_thread.start()

    collapsed_findings: List[Violation] = []
    for index, findings in all_findings:
        tool_id = tools[index].tool_id
        if isinstance(findings, Exception):
            echo_error(f"Error while running {tool_id}: {findings}")
            if isinstance(findings, subprocess.CalledProcessError):
                click.secho(findings.stderr, err=True)
            click.echo("", err=True)
            is_error = True
        elif isinstance(findings, list) and findings:
            findings_to_log += bento.metrics.violations_to_metrics(
                tool_id, findings, get_ignores_for_tool(tool_id, config)
            )
            collapsed_findings += [f for f in findings if not f.filtered]

    if collapsed_findings:
        findings_by_path = sorted(collapsed_findings, key=by_path)
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


@cli.command()
def install_hook():
    """
        Installs bento as a git pre-commit hook
        Saves any existing pre-commit hook to .git/hooks/pre-commit.pre-bento and
        runs said hook after bento hook is run
    """
    # Get hook path
    try:
        repo = git.Repo(os.getcwd(), search_parent_directories=True)
        hook_path = git.index.fun.hook_path("pre-commit", repo.git_dir)
    except Exception:
        raise

    legacy_hook_path = f"{hook_path}.pre-bento"
    if os.path.exists(hook_path):
        # If pre-commit hook already exists move it over
        if os.path.exists(legacy_hook_path):
            raise Exception(
                "There is already a legacy hook. Not sure what to do so just exiting for now."
            )
        else:
            shutil.move(hook_path, legacy_hook_path)

    # Copy pre-commit script template to hook_path
    template_location = os.path.join(
        os.path.dirname(__file__), "resources/pre-commit.template"
    )
    shutil.copyfile(template_location, hook_path)

    # Make file executable
    original_mode = os.stat(hook_path).st_mode
    os.chmod(hook_path, original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)