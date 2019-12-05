import logging
import os
import sys
from typing import Any, Dict, Optional

import click
from packaging.version import Version

import bento.constants as constants
import bento.decorators
import bento.extra
import bento.git
import bento.metrics
import bento.tool_runner
import bento.util
from bento.context import Context
from bento.network import post_metrics
from bento.util import (
    echo_box,
    echo_error,
    echo_newline,
    echo_warning,
    echo_wrap,
    persist_global_config,
    read_global_config,
    wrap_link,
)


def _validate_interactivity() -> None:
    """
    Validates that this Bento session is running interactively

    :raises: SystemExit(3) if not interactive
    """
    is_interactive = sys.stdin.isatty() and sys.stderr.isatty()
    if not is_interactive:
        echo_error("This installation of Bento is not registered.")
        click.secho(
            """Please either:
◦ Register Bento by running it in an interactive terminal
◦ Run Bento with `--agree --email [EMAIL]`""",
            err=True,
        )
        sys.exit(3)


def _show_welcome_message(agree: bool, email: Optional[str]) -> None:
    """
    Displays a 'welcome to Bento' message

    Message is only displayed if registration is not skipped via command-line arguments

    :param agree: If the user has agreed to all prompts via the command line
    :param email: The user's email, if supplied via command line
    """
    if not agree or email is None:
        echo_box("Global Bento Configuration")
        echo_wrap(
            "Thanks for installing Bento, a free and opinionated toolkit for gradually adopting linters and "
            "program analysis in your codebase!"
        )
        echo_newline()
        echo_wrap(
            "Registration: "
            + click.style(
                "We’ll use your email to provide support and share product updates. You can unsubscribe at any time.",
                dim=True,
            )
        )
        echo_newline()


def _update_email(
    global_config: Dict[str, Any], context: Context, email: Optional[str] = None
) -> bool:
    """
    Updates the user's global config with their email address

    If the user has passed an email on the command line, this logic is skipped.
    """
    if not email and "email" not in global_config:
        # import inside def for performance
        from validate_email import validate_email

        email = None
        while not (email and validate_email(email)):
            context.start_user_timer()
            _validate_interactivity()
            email = click.prompt(
                "What is your email address?", type=str, default=bento.git.user_email()
            )
            context.stop_user_timer()
            echo_newline()

        r = _post_email_to_mailchimp(email)
        if not r:
            echo_warning(
                "\nWe were unable to subscribe you to the Bento mailing list (which means you may miss out on "
                "announcements!). Bento will continue running. Please shoot us a note via support@r2c.dev to debug. "
            )

        global_config["email"] = email
        persist_global_config(global_config)

    return True


def _post_email_to_mailchimp(email: str) -> bool:
    """
    Subscribes this email to the Bento mailing list

    :return: Mailchimp's response status
    """
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


def _confirm_tos_update(context: Context, global_config: Dict[str, Any]) -> bool:
    """
    Interactive process to confirm updated agreement to the Terms of Service

    :return: If the user has agreed to the updated ToS
    """

    if global_config is None or constants.TERMS_OF_SERVICE_KEY not in global_config:
        echo_wrap(
            "Privacy: "
            + click.style(
                "We take privacy seriously. Bento runs exclusively on your computer. It will never send your code anywhere.",
                dim=True,
            )
        )
        echo_newline()
        # this message is shown if the user has never agreed to the TOS
        link_text = "bento.dev/privacy"
        tos_message = wrap_link(
            "We’re constantly looking to make Bento better. To that end, we collect limited usage and results "
            f"data. To learn more, see {link_text}.",
            0,
            (link_text, "https://bento.dev/privacy"),
            dim=True,
        )
    else:
        # We care that the user has agreed to the current terms of service
        tos_version = global_config[constants.TERMS_OF_SERVICE_KEY]

        try:
            agreed_to_version = Version(tos_version)
            if agreed_to_version == Version(constants.TERMS_OF_SERVICE_VERSION):
                logging.info("User ToS agreement is current")
                return True
        except Exception:
            echo_error(
                f"""Invalid version for `{constants.TERMS_OF_SERVICE_KEY}` in {constants.GLOBAL_CONFIG_PATH}: {tos_version}.
  Please remove {constants.GLOBAL_CONFIG_PATH} and re-run Bento."""
            )
            return False

        # we only return from the try block if the user has agreed to an older version of the TOS
        link_text = "support@r2c.dev"
        tos_message = wrap_link(
            "We've made changes to our terms of service. Please review the new terms. If you have any questions "
            f"or concerns please reach out via {link_text}.",
            0,
            (link_text, "mailto:support@r2c.dev"),
            dim=True,
        )

    # the case where the user never agreed to the TOS or agreed to an earlier version
    click.echo(tos_message, err=True)
    echo_newline()

    context.start_user_timer()
    _validate_interactivity()
    agreed = click.confirm(
        "Continue and agree to Bento's terms of service and privacy policy?",
        default=True,
    )
    echo_newline()
    context.stop_user_timer()

    if agreed:
        global_config[
            constants.TERMS_OF_SERVICE_KEY
        ] = constants.TERMS_OF_SERVICE_VERSION

        persist_global_config(global_config)
        return True
    else:
        echo_error(constants.TERMS_OF_SERVICE_ERROR)
        return False


def _suggest_autocomplete() -> None:
    """
    Suggests code to add to the user's shell config to set up autocompletion
    """
    if "SHELL" not in os.environ:
        return

    shell = os.environ["SHELL"]
    common_text = "Bento supports tab autocompletion. To enable, run:\n"

    if shell.endswith("/zsh"):
        cmd_text = (
            "echo -e '\\neval \"$(_BENTO_COMPLETE=source_zsh bento)\"' >> ~/.zshrc"
        )
    elif shell.endswith("/bash"):
        cmd_text = "echo -e '\\neval \"$(_BENTO_COMPLETE=source bento)\"' >> ~/.bashrc"
    else:
        return

    echo_wrap(common_text)
    echo_newline()
    click.secho(f"  $ {click.style(cmd_text, bold=True)}", err=True)


def verify_registration(agree: bool, email: Optional[str], context: Context) -> bool:
    """
    Performs all necessary steps to ensure user registration:

    - Global config exists
    - User has agreed to Terms of Service
    - User has registered with email

    :param agree: If True, automatically confirms all yes/no prompts
    :param email: If exists, registers with this email
    :param context: The CLI context
    :return: Whether the user is properly registered after this function terminates
    """

    global_config = read_global_config()
    first_run = False
    if global_config is None:
        first_run = True
        global_config = {}
        _show_welcome_message(agree, email)

    registration_email = email or os.environ.get(constants.BENTO_EMAIL_VAR)
    _update_email(global_config, context, email=registration_email)

    if not agree and not _confirm_tos_update(context, global_config):
        return False

    if first_run and not agree:
        _suggest_autocomplete()

    return True
