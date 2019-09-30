import os
import pkgutil
import shutil
import subprocess
import sys
from importlib import import_module
from typing import List, Pattern, Type

import click
import psutil


def for_name(name: str) -> Type:
    """
    Reflectively obtains a type from a python identifier

    E.g.
        for_name("bento.extra.eslint.EslintTool")
    returns the EslintTool type

    Parameters:
        name (str): The type name, as a python fully qualified identifier
    """
    module_name, class_name = name.rsplit(".", 1)
    mod = import_module(module_name)
    return getattr(mod, class_name)


def is_child_process_of(pattern: Pattern) -> bool:
    """
    Returns true iff this process is a child process of a process whose name matches pattern
    """
    me = psutil.Process()
    parents = me.parents()
    matches = iter(0 for p in parents if pattern.search(p.name()))
    return next(matches, None) is not None


def package_subclasses(type: Type, pkg_path: str) -> List[Type]:
    """
    Finds all subtypes of a type within a module path, relative to this module

    Parameters:
        type: The parent type
        pkg_path: The path to search, written as a python identifier (e.g. bento.extra)

    Returns:
        A list of all subtypes
    """
    walk_path = os.path.join(
        os.path.dirname(__file__), os.path.pardir, *pkg_path.split(".")
    )
    for (_, name, ispkg) in pkgutil.walk_packages([walk_path]):
        if name != "setup" and not ispkg:
            import_module(f"{pkg_path}.{name}", __package__)

    return type.__subclasses__()


def less(text: List[str], only_if_overrun: bool = False) -> None:
    """
    Prints a string through less
    """
    joined = "\n".join(text)
    use_echo = False

    if not sys.stdout.isatty():
        use_echo = True
    if only_if_overrun:
        _, height = shutil.get_terminal_size()
        if len(text) < height:
            use_echo = True

    if use_echo:
        click.echo(joined)
    else:
        process = subprocess.Popen(["less", "-r"], stdin=subprocess.PIPE)
        process.stdin.write(bytearray(joined, "utf8"))
        process.communicate()


def echo_error(text: str, indent: str = "") -> None:
    click.secho(f"{indent}✘ {text}", fg="red")


def echo_warning(text: str, indent: str = "") -> None:
    click.secho(f"{indent}⚠ {text}", fg="yellow")


def echo_success(text: str, indent: str = "") -> None:
    click.secho(f"{indent}✔ {text}", fg="green")
