import logging
import os
import sys
from typing import Any, Optional, Union

import click
import requests
import yaml
from semantic_version import Version

import bento.constants as constants
import bento.decorators
import bento.extra
import bento.git
import bento.metrics
import bento.tool_runner
import bento.util
from bento.commands import archive, check, hook, init, update_ignores
from bento.context import Context
from bento.network import fetch_latest_version, post_metrics
from bento.util import echo_error, echo_warning

UPGRADE_WARNING_OUTPUT = f"""
╭─────────────────────────────────────────────╮
│  🎉 A new version of Bento is available 🎉  │
│  Try it out by running:                     │
│                                             │
│       {click.style("pip3 install --upgrade bento-cli", fg="blue")}      │
│                                             │
╰─────────────────────────────────────────────╯
"""

TERMS_OF_SERVICE_MESSAGE = f"""│ We’re constantly looking for ways to make Bento better! To that end, we
│ anonymously report usage statistics to improve the tool over time. Bento runs
│ on your local machine and never sends your code anywhere or to anyone. Learn
│ more at https://github.com/returntocorp/bento/blob/master/PRIVACY.md.
"""

TERMS_OF_SERVICE_ERROR = f"""
Bento did NOT install. Bento beta users must agree to the terms of service to continue. Please reach out to us at support@r2c.dev with questions or concerns.
"""


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
    email = email.strip("\"'")
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
        email = click.prompt("Email", type=str, default=bento.git.user_email())
        global_config["email"] = email
        r = __post_email_to_mailchimp(email)
        if not r:
            echo_warning(
                "\nWe were unable to subscribe you to the Bento mailing list, but will continue with installation. Please shoot us a note via support@r2c.dev to debug."
            )

    _suggest_autocomplete()

    os.makedirs(constants.GLOBAL_CONFIG_DIR, exist_ok=True)
    with open(constants.GLOBAL_CONFIG_PATH, "w+") as yaml_file:
        yaml.safe_dump(global_config, yaml_file)

    click.echo(f"\nCreated user configs at {constants.GLOBAL_CONFIG_PATH}.")

    return True


@click.group()
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
@click.pass_context
def cli(ctx: click.Context, base_path: Optional[str], agree: bool) -> None:
    __setup_logging()
    is_init = ctx.invoked_subcommand == "init"
    if base_path is None:
        ctx.obj = Context(is_init=is_init)
    else:
        ctx.obj = Context(base_path=base_path, is_init=is_init)
    if not is_running_supported_python3():
        echo_error(
            "Bento requires Python 3.6+. Please ensure you have Python 3.6+ and installed Bento via `pip3 install bento-cli`."
        )
        sys.exit(3)
    if not agree and not has_completed_registration():
        registered = register_user()
        logging.error("User did not complete registration")
        if not registered:
            # Terminate with non-zero error
            sys.exit(3)
    if not is_running_latest():
        logging.warning("Bento client is outdated")
        click.echo(UPGRADE_WARNING_OUTPUT)


cli.add_command(archive.archive)
cli.add_command(check.check)
cli.add_command(init.init)
cli.add_command(hook.install_hook)
cli.add_command(update_ignores.enable)
cli.add_command(update_ignores.disable)
