import logging
import subprocess
import sys
import time
from datetime import datetime
from functools import update_wrapper
from typing import Any, Callable, Optional

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
            cmd = " ".join(e.cmd)
        echo_warning(f'Could not execute "{cmd}":\n{e.stderr}')
        logging.error(e.stdout)
        logging.error(e.stderr)
    else:
        echo_error(f"There was an exception {e}")


def with_metrics(f: _AnyCallable) -> _AnyCallable:
    def new_func(*args: Any, **kwargs: Any) -> Any:
        exit_code = 0
        exception: Optional[Exception] = None
        before = time.time()

        context = click.get_current_context()
        command = context.command.name
        cli_context = context.obj
        timestamp = (
            cli_context.timestamp if cli_context else datetime.utcnow().isoformat("T")
        )
        logging.info(f"Executing {command}")

        try:
            res = f(*args, **kwargs)
        except SystemExit as e:
            exit_code = e.code
        except Exception as e:
            exception = e
            exit_code = 3
            __log_exception(e)

        elapsed = time.time() - before
        user_duration = cli_context.user_duration() if cli_context else None
        logging.info(f"{command} completed in {elapsed} with exit code {exit_code}")
        bento.network.post_metrics(
            bento.metrics.command_metric(
                command, timestamp, kwargs, exit_code, elapsed, exception, user_duration
            )
        )
        if exit_code != 0:
            sys.exit(exit_code)
        return res

    return update_wrapper(new_func, f)
