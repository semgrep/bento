#!/usr/bin/env python3
import subprocess
import sys
import traceback

import requests

from bento.cli import cli
from bento.util import echo_error, echo_warning


def main():
    try:
        cli()
    except subprocess.CalledProcessError as e:
        cmd = e.cmd
        if isinstance(e.cmd, list):
            cmd = " ".join(e.cmd)
        echo_warning(f'Could not execute "{cmd}":\n{e.stderr}')
    except requests.exceptions.HTTPError:
        echo_warning(f"Network issue during metric collection.")
    except Exception as e:
        traceback.print_exc()
        echo_error(f"There was an exception {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
