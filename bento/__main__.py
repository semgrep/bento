#!/usr/bin/env python3
import subprocess
import traceback

from bento.cli import cli


def main():
    try:
        cli()
    except subprocess.CalledProcessError as e:
        print(f'Could not execute "{" ".join(e.cmd)}":\n{e.stderr}')
    except Exception as e:
        traceback.print_exc()
        print("There was an exception", e)


if __name__ == "__main__":
    main()
