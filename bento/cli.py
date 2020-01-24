import logging
import os
import sys
from distutils.util import strtobool
from typing import Optional

import click
from packaging.version import Version

import bento.constants as constants
from bento.commands import archive, check, disable, enable, init, register
from bento.context import Context
from bento.network import fetch_latest_version
from bento.util import echo_error


def _setup_logging() -> None:
    os.makedirs(os.path.dirname(constants.DEFAULT_LOG_PATH), exist_ok=True)
    logging.basicConfig(
        filename=constants.DEFAULT_LOG_PATH,
        level=logging.DEBUG,
        filemode="w",
        format="[%(levelname)s] %(relativeCreated)s %(name)s:%(module)s - %(message)s",
    )
    logging.info(
        f"Environment: stdout.isatty={sys.stdout.isatty()} stderr.isatty={sys.stderr.isatty()} stdin.isatty={sys.stdin.isatty()}"
    )


def _is_test() -> bool:
    test_var = os.getenv(constants.BENTO_TEST_VAR, "0")
    try:
        return strtobool(test_var) == 1
    except ValueError:
        return False


def _is_running_latest() -> bool:
    latest_version, _ = fetch_latest_version()
    current_version = _get_version()
    logging.info(
        f"Current bento version is {current_version}, latest is {latest_version}"
    )
    if latest_version and Version(current_version) < Version(latest_version):
        return False
    return True


def _get_version() -> str:
    """Get the current r2c-cli version based on __init__"""
    from bento import __version__

    return __version__


def _is_running_supported_python3() -> bool:
    python_major_v = sys.version_info.major
    python_minor_v = sys.version_info.minor
    logging.info(f"Python version is ({python_major_v}.{python_minor_v})")
    return python_major_v >= 3 and python_minor_v >= 6


@click.group(epilog="To get help for a specific command, run `bento COMMAND --help`")
@click.help_option("-h", "--help")
@click.version_option(
    prog_name="bento", version=_get_version(), message="%(prog)s/%(version)s"
)
@click.option(
    "--base-path",
    help=f"Path to the project to run bento in.",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    hidden=True,
)
@click.option(
    "--agree",
    is_flag=True,
    help="Automatically agree to terms of service.",
    default=False,
)
@click.option(
    "--email",
    type=str,
    help="Email address to use while running this command without global configs e.g. in CI",
    default=None,
)
@click.pass_context
def cli(
    ctx: click.Context, base_path: Optional[str], agree: bool, email: Optional[str]
) -> None:
    _setup_logging()
    is_init = ctx.invoked_subcommand == "init"
    ctx.help_option_names = ["-h", "--help"]
    if base_path is None:
        ctx.obj = Context(is_init=is_init, email=email)
    else:
        ctx.obj = Context(base_path=base_path, is_init=is_init, email=email)
    if not _is_running_supported_python3():
        echo_error(
            "Bento requires Python 3.6+. Please ensure you have Python 3.6+ and installed Bento via `pip3 install bento-cli`."
        )
        sys.exit(3)

    registrar = register.Registrar(ctx, agree, email=email)
    if not registrar.verify():
        logging.error("Could not verify the user's registration.")
        sys.exit(3)
    if not _is_running_latest() and not _is_test():
        logging.warning("Bento client is outdated")
        click.echo(constants.UPGRADE_WARNING_OUTPUT)


cli.add_command(archive.archive)
cli.add_command(check.check)
cli.add_command(init.init)
cli.add_command(enable.enable)
cli.add_command(disable.disable)
