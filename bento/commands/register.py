import logging
import os
import sys
from typing import Any, Dict, Optional

import attr
import click
from packaging.version import InvalidVersion, Version

import bento.constants as constants
import bento.decorators
import bento.extra
import bento.git
import bento.metrics
import bento.tool_runner
import bento.util
from bento.context import Context
from bento.network import post_metrics
from bento.renderer import Renderer
from bento.util import echo_newline, persist_global_config, read_global_config


@attr.s(auto_attribs=True)
class Registrar(object):
    context: Context
    agree: bool
    is_first_run: bool = False
    global_config: Dict[str, Any] = attr.ib(default=read_global_config(), init=False)
    email: Optional[str] = attr.ib()
    renderer: Renderer = Renderer(constants.REGISTRATION_CONTENT_PATH)

    @email.default
    def _get_email_from_environ(self) -> Optional[str]:
        return os.environ.get(constants.BENTO_EMAIL_VAR)

    def __attrs_post_init__(self) -> None:
        if self.global_config is None:
            self.is_first_run = True
            self.global_config = {}

    def _validate_interactivity(self) -> None:
        """
        Validates that this Bento session is running interactively

        :raises: SystemExit(3) if not interactive
        """
        is_interactive = sys.stdin.isatty() and sys.stderr.isatty()
        if not is_interactive:
            self.renderer.echo("not-registered")
            sys.exit(3)

    def _show_welcome_message(self) -> None:
        """
        Displays a 'welcome to Bento' message

        Message is only displayed if registration is not skipped via command-line arguments

        :param agree: If the user has agreed to all prompts via the command line
        :param email: The user's email, if supplied via command line
        """
        if (
            self.email is None
            and "email" not in self.global_config
            or not self.agree
            and constants.TERMS_OF_SERVICE_KEY not in self.global_config
        ):
            self.renderer.echo("welcome")

    def _update_email(self) -> None:
        """
        Updates the user's global config with their email address

        If the user has passed an email on the command line, this logic is skipped.
        """
        # import inside def for performance
        from validate_email import validate_email

        valid_configured_email = False
        if "email" in self.global_config:
            configured_email = self.global_config.get("email")
            if configured_email is not None:
                valid_configured_email = validate_email(configured_email)

        if (
            not self.email or not validate_email(self.email)
        ) and not valid_configured_email:
            self.renderer.echo("update-email", "leader")

            email = None
            while not (email and validate_email(email)):
                self.context.start_user_timer()
                self._validate_interactivity()
                email = click.prompt(
                    self.renderer.text_at("update-email", "prompt"),
                    type=str,
                    default=bento.git.user_email(),
                )
                self.context.stop_user_timer()
                echo_newline()

            r = self._post_email_to_mailchimp(email)
            if not r:
                self.renderer.echo("update-email", "failure")

            self.global_config["email"] = email
            persist_global_config(self.global_config)

    @staticmethod
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

    def _confirm_tos_update(self) -> bool:
        """
        Interactive process to confirm updated agreement to the Terms of Service

        :return: If the user has agreed to the updated ToS
        """
        if constants.TERMS_OF_SERVICE_KEY not in self.global_config:
            self.renderer.echo("confirm-tos", "fresh")
        else:
            # We care that the user has agreed to the current terms of service
            tos_version = self.global_config[constants.TERMS_OF_SERVICE_KEY]

            try:
                agreed_to_version = Version(tos_version)
                if agreed_to_version == Version(constants.TERMS_OF_SERVICE_VERSION):
                    logging.info("User ToS agreement is current")
                    return True
            except InvalidVersion:
                self.renderer.echo("confirm-tos", "invalid-version")
                sys.exit(3)

            self.renderer.echo("confirm-tos", "upgrade")

        self.context.start_user_timer()
        self._validate_interactivity()
        agreed = click.confirm(
            "Continue and agree to Bento's terms of service and privacy policy?",
            default=True,
        )
        echo_newline()
        self.context.stop_user_timer()

        if agreed:
            self.global_config[
                constants.TERMS_OF_SERVICE_KEY
            ] = constants.TERMS_OF_SERVICE_VERSION

            persist_global_config(self.global_config)
            return True
        else:
            self.renderer.echo("confirm-tos", "error")
            return False

    def _suggest_autocomplete(self) -> None:
        """
        Suggests code to add to the user's shell config to set up autocompletion
        """
        if "SHELL" not in os.environ:
            return

        shell = os.environ["SHELL"]

        if shell.endswith("/zsh"):
            self.renderer.echo("suggest-autocomplete", "zsh")
        elif shell.endswith("/bash"):
            self.renderer.echo("suggest-autocomplete", "bash")
        else:
            return

    def verify(self) -> bool:
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

        self._show_welcome_message()
        self._update_email()

        if not self.agree and not self._confirm_tos_update():
            return False

        if self.is_first_run and not self.agree:
            self._suggest_autocomplete()

        return True
