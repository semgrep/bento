#!/usr/bin/env python3
import logging
import subprocess
import sys

import requests

from bento.cli import cli
from bento.util import echo_error, echo_warning


def main() -> None:
    try:
        cli()
    except Exception as e:
        logging.error(e)
        logging.error(sys.exc_info())
        if isinstance(e, subprocess.CalledProcessError):
            cmd = e.cmd
            if isinstance(e.cmd, list):
                cmd = " ".join(e.cmd)
            echo_warning(f'Could not execute "{cmd}":\n{e.stderr}')
            logging.error(e.stdout)
            logging.error(e.stderr)
            sys.exit(3)
        elif isinstance(e, requests.exceptions.HTTPError):
            logging.warn(f"Network issue during metric collection.")
        else:
            echo_error(f"There was an exception {e}")
            sys.exit(3)


if __name__ == "__main__":
    main()
