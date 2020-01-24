import logging
import subprocess
import sys
import time
from datetime import datetime
from functools import update_wrapper
from typing import Any, Callable

import click

import bento.metrics
import bento.network
from bento.util import echo_error, echo_warning

_AnyCallable = Callable[..., Any]


def __log_exception(e: Exception) -> None:
    logging.exception(e)
    if isinstance(e, subprocess.CalledProcessError):
        cmd = e.cmd
        if isinstance(e.cmd, list):
            cmd = " ".join([str(part) for part in e.cmd])
        echo_warning(f'Could not execute "{cmd}":\n{e.stderr}')
        logging.error(e.stdout)
        logging.error(e.stderr)
    else:
        echo_error(f"There was an exception {e}")


def with_metrics(f: _AnyCallable) -> _AnyCallable:
    def new_func(*args: Any, **kwargs: Any) -> Any:
        exit_code = 0
        before = time.time()

        context = click.get_current_context()

        if context.parent and context.parent.parent:
            # this is a command with a subcommand e.g. `bento disable check <tool> <check>`
            command = context.parent.command.name
        else:
            command = context.command.name

        cli_context = context.obj
        timestamp = (
            cli_context.timestamp if cli_context else datetime.utcnow().isoformat("T")
        )
        logging.info(f"Executing {command}")

        exc_name = None
        try:
            res = f(*args, **kwargs)
        except KeyboardInterrupt as e:
            # KeyboardInterrupt is a BaseException and has no exit code. Use 130 to mimic bash behavior.
            exit_code = 130
            exc_name = e.__class__.__name__
        except SystemExit as e:
            exit_code = e.code
            exc_name = e.__class__.__name__
        except Exception as e:
            exit_code = 3
            __log_exception(e)
            exc_name = e.__class__.__name__

        elapsed = time.time() - before
        user_duration = cli_context.user_duration() if cli_context else None

        if exc_name == "KeyboardInterrupt":
            logging.info(f"{command} interrupted after running for {elapsed}s")
        else:
            logging.info(
                f"{command} completed in {elapsed}s with exit code {exit_code}"
            )

        email = (
            cli_context.email
            if cli_context and cli_context.email
            else bento.metrics.read_user_email()
        )

        bento.network.post_metrics(
            bento.metrics.command_metric(
                command,
                email,
                timestamp,
                kwargs,
                exit_code,
                elapsed,
                exc_name,
                user_duration,
            )
        )
        if exit_code != 0:
            sys.exit(exit_code)
        return res

    return update_wrapper(new_func, f)
