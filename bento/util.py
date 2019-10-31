from __future__ import unicode_literals

import itertools
import logging
import os
import os.path
import pkgutil
import shutil
import signal
import subprocess
import sys
import threading
import types
from importlib import import_module
from pathlib import Path
from typing import Collection, List, Optional, Pattern, Tuple, Type, Union

import click
import psutil
from frozendict import frozendict

EMPTY_DICT = frozendict({})

AutocompleteSuggestions = List[Union[str, Tuple[str, str]]]


def fetch_line_in_file(path: Path, line_number: int) -> Optional[str]:
    """
    `line_number` is one-indexed! Returns the line if it can be found, returns None if the path doesn't exist
    """
    if not path.exists():
        return None
    with path.open(buffering=1) as fin:  # buffering=1 turns on line-level reads
        return next(itertools.islice(fin, line_number - 1, line_number), None)


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


def package_subclasses(tpe: Type, pkg_path: str) -> List[Type]:
    """
    Finds all subtypes of a type within a module path, relative to this module

    Parameters:
        tpe: The parent type
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

    return tpe.__subclasses__()


def less(
    text: Collection[str], pager: bool = True, only_if_overrun: bool = False
) -> None:
    """
    Possibly prints a string through less.

    Parameters:
        pager: If false, the string is always echoed directly to stdout
        only_if_overrun: If true, the strings are only printed through less if their length exceeds the terminal height
    """
    use_echo = False
    text_len = len(text)

    # In order to prevent an early pager exit from killing the CLI,
    # we must both ignore the resulting SIGPIPE and BrokenPipeError
    def drop_sig(signal: int, frame: Optional[types.FrameType]) -> None:
        pass

    if not pager or not sys.stdout.isatty():
        use_echo = True
    if only_if_overrun:
        _, height = shutil.get_terminal_size()
        if text_len < height:
            use_echo = True

    if use_echo:
        for t in text:
            click.echo(t)
    else:
        # NOTE: Using signal.SIG_IGN here DOES NOT IGNORE the resulting SIGPIPE
        signal.signal(signal.SIGPIPE, drop_sig)
        try:
            process = subprocess.Popen(["less", "-r"], stdin=subprocess.PIPE)
            for ix, t in enumerate(text):
                process.stdin.write(bytearray(t, "utf8"))
                if ix != text_len - 1:
                    process.stdin.write(bytearray("\n", "utf8"))
            process.communicate()
        except BrokenPipeError:
            pass
        finally:
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def echo_error(text: str, indent: str = "") -> None:
    logging.error(text)
    click.secho(f"{indent}✘ {text}", fg="red", err=True)


def echo_warning(text: str, indent: str = "") -> None:
    logging.warning(text)
    click.secho(f"{indent}⚠ {text}", fg="yellow", err=True)


def echo_success(text: str, indent: str = "") -> None:
    logging.info(text)
    click.secho(f"{indent}✔ {text}", fg="green", err=True)


# Taken from http://www.madhur.co.in/blog/2015/11/02/countdownlatch-python.html
class CountDownLatch(object):
    def __init__(self, count: int = 1):
        self.count = count
        self.lock = threading.Condition()

    def count_down(self) -> None:
        with self.lock:
            self.count -= 1
            if self.count <= 0:
                self.lock.notifyAll()

    def wait_for(self) -> None:
        with self.lock:
            while self.count > 0:
                self.lock.wait()
