import logging
import os
import sys
from typing import Any, Dict, Optional, Union

import click
from semantic_version import Version

import bento.constants as constants
import bento.decorators
import bento.extra
import bento.git
import bento.metrics
import bento.tool_runner
import bento.util
from bento.commands import archive, check, disable, enable, hook, init
from bento.context import Context
from bento.network import fetch_latest_version, post_metrics
from bento.util import (
    echo_error,
    echo_warning,
    persist_global_config,
    read_global_config,
)


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


def __post_email_to_mailchimp(email: str) -> bool:
    # import inside def for performance
    import requests

    r = requests.post(
        "https://waitlist.r2c.dev/subscribe", json={"email": email}, timeout=5
    )
    status = r.status_code == requests.codes.ok
    data = [
        {
            "message": "Tried adding user to Bento waitlist",
            "user-email": email,
            "mailchimp_response": r.status_code,
            "success": status,
        }
    ]
    logging.info(f"Registering user with data {data}")
    post_metrics(data)
    return status


def is_running_supported_python3() -> bool:
    python_major_v = sys.version_info.major
    python_minor_v = sys.version_info.minor
    logging.info(f"Python version is ({python_major_v}.{python_minor_v})")
    return python_major_v >= 3 and python_minor_v >= 6


def confirm_tos_update(context: Context, global_config: Dict[str, Any]) -> bool:
    if global_config is None or constants.TERMS_OF_SERVICE_KEY not in global_config:
        # this message is shown if the user has never agreed to the TOS
        tos_message = (
            "To get started for the first time, please review our terms of service"
        )
    else:
        # We care that the user has agreed to the current terms of service
        tos_version = global_config[constants.TERMS_OF_SERVICE_KEY]

        try:
            agreed_to_version = Version(version_string=tos_version)
            if agreed_to_version == Version(
                version_string=constants.TERMS_OF_SERVICE_VERSION
            ):
                return True
        except Exception:
            bento.util.echo_error(
                f"Invalid semver for `{constants.TERMS_OF_SERVICE_KEY}` in {constants.GLOBAL_CONFIG_PATH}: {tos_version}. Deleting the key/value and re-running Bento should resolve the issue."
            )
            return False

        # we only return from the try block if the user has agreed to an older version of the TOS
        tos_message = "We've made changes to our terms of service. Please review the new terms. If you have any questions or concerns please reach out via support@r2c.dev."

    # the case where the user never agreed to the TOS or agreed to an earlier version
    click.echo(f"{tos_message}:\n\n{constants.TERMS_OF_SERVICE_MESSAGE}")

    context.start_user_timer()
    agreed = click.confirm(
        "Do you agree to Bento's terms of service and privacy policy?", default=True
    )
    context.stop_user_timer()

    if agreed:
        global_config[
            constants.TERMS_OF_SERVICE_KEY
        ] = constants.TERMS_OF_SERVICE_VERSION

        persist_global_config(global_config)
    else:
        bento.util.echo_error(constants.TERMS_OF_SERVICE_ERROR)
        return False

    return True


def _suggest_autocomplete() -> None:
    if "SHELL" not in os.environ:
        return
    shell = os.environ["SHELL"]
    if shell.endswith("/zsh"):
        click.echo(
            """
╭────────────────────────────────────────────────────────────────────╮
│           🍱 To enable zsh autocompletion please run 🍱            │
│                                                                    │
│ echo -e '\\neval "$(_BENTO_COMPLETE=source_zsh bento)"' >> ~/.zshrc │
│                                                                    │
╰────────────────────────────────────────────────────────────────────╯
"""
        )
    elif shell.endswith("/bash"):
        click.echo(
            """
╭─────────────────────────────────────────────────────────────────╮
│         🍱 To enable bash autocompletion please run 🍱          │
│                                                                 │
│ echo -e '\\neval "$(_BENTO_COMPLETE=source bento)"' >> ~/.bashrc │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
"""
        )


def update_email(
    global_config: Dict[str, Any], context: Context, email: Optional[str] = None
) -> bool:
    if not email and "email" not in global_config:
        # import inside def for performance
        from validate_email import validate_email

        click.echo(
            "For the Bento beta, we may contact you infrequently via email to ask for your feedback and let you know about updates. You can unsubscribe at any time."
        )

        email = None
        while not (email and validate_email(email)):
            context.start_user_timer()
            email = click.prompt("Email", type=str, default=bento.git.user_email())
            context.stop_user_timer()

        r = __post_email_to_mailchimp(email)
        if not r:
            echo_warning(
                "\nWe were unable to subscribe you to the Bento mailing list (which means you may miss out on announcements!). Bento will continue running. Please shoot us a note via support@r2c.dev to debug."
            )

        global_config["email"] = email
        persist_global_config(global_config)

    return True


def verify_registration(agree: bool, email: Optional[str], context: Context) -> bool:
    global_config = read_global_config()
    first_run = False
    if global_config is None:
        first_run = True
        global_config = {}

        # only show welcome message if running in interactive mode
        if not agree or email is None:
            bolded_welcome = click.style(f"Welcome to Bento!", bold=True)
            click.echo(
                f"{bolded_welcome} You're about to get a powerful suite of tailored tools.\n"
            )

    if not agree and not confirm_tos_update(context, global_config):
        return False

    update_email(
        global_config,
        context,
        email=(email or os.environ.get(constants.BENTO_EMAIL_VAR)),
    )

    if first_run and not agree:
        _suggest_autocomplete()

    return True


@click.group(epilog="To get help for a specific command, run `bento COMMAND --help`")
@click.help_option("-h", "--help")
@click.option(
    "--version",
    is_flag=True,
    help="Show current version bento.",
    callback=_print_version,
    expose_value=False,
    is_eager=True,
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
    if not verify_registration(agree, email, ctx.obj):
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
