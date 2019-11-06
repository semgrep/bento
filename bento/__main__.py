#!/usr/bin/env python3
from bento.cli import cli


def main() -> None:
    cli(auto_envvar_prefix="BENTO")


if __name__ == "__main__":
    main()
