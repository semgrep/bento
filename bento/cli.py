import logging
import os
import sys
from typing import Any, Optional, Union

import click
from packaging.version import Version

import bento.constants as constants
from bento.commands import archive, check, disable, enable, hook, init, register
from bento.context import Context
from bento.network import fetch_latest_version
from bento.util import echo_error


def __setup_logging() -> None:
    os.makedirs(os.path.dirname(constants.DEFAULT_LOG_PATH), exist_ok=True)
    logging.basicConfig(
        filename=constants.DEFAULT_LOG_PATH,
        level=logging.DEBUG,
        filemode="w",
        format="[%(levelname)s] %(relativeCreated)s %(name)s:%(module)s - %(message)s",
    )


def is_running_latest() -> bool:
    latest_version, _ = fetch_latest_version()
    current_version = get_version()
    logging.info(
        f"Current bento version is {current_version}, latest is {latest_version}"
    )
    if latest_version and Version(current_version) < Version(latest_version):
        return False
    return True


def get_version() -> str:
    """Get the current r2c-cli version based on __init__"""
    from bento import __version__

    return __version__


def _print_version(
    ctx: click.Context, param: Union[click.Option, click.Parameter], value: Any
) -> None:
    """Print the current r2c-cli version based on setuptools runtime"""
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"bento/{get_version()}")
    ctx.exit()


def is_running_supported_python3() -> bool:
    python_major_v = sys.version_info.major
    python_minor_v = sys.version_info.minor
    logging.info(f"Python version is ({python_major_v}.{python_minor_v})")
    return python_major_v >= 3 and python_minor_v >= 6


@click.group(epilog="To get help for a specific command, run `bento COMMAND --help`")
@click.help_option("-h", "--help")
@click.version_option(
    prog_name="bento", version=get_version(), message="%(prog)s/%(version)s"
)
@click.option(
    "--base-path",
    help="Path to the directory containing the code, as well as the .bento.yml file.",
    type=click.Path(exists=True, file_okay=False),
    default=None,
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
    __setup_logging()
    is_init = ctx.invoked_subcommand == "init"
    ctx.help_option_names = ["-h", "--help"]
    if base_path is None:
        ctx.obj = Context(is_init=is_init)
    else:
        ctx.obj = Context(base_path=base_path, is_init=is_init)
    if not is_running_supported_python3():
        echo_error(
            "Bento requires Python 3.6+. Please ensure you have Python 3.6+ and installed Bento via `pip3 install bento-cli`."
        )
        sys.exit(3)

    registrar = register.Registrar(ctx.obj, agree, email=email)
    if not registrar.verify():
        logging.error("Could not verify the user's registration.")
        sys.exit(3)
    if not is_running_latest():
        logging.warning("Bento client is outdated")
        click.echo(constants.UPGRADE_WARNING_OUTPUT)


cli.add_command(archive.archive)
cli.add_command(check.check)
cli.add_command(init.init)
cli.add_command(hook.install_hook)
cli.add_command(enable.enable)
cli.add_command(disable.disable)
