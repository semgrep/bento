from __future__ import unicode_literals

import contextlib
import errno
import os
import os.path
import pkgutil
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from importlib import import_module
from importlib.resources import open_binary, read_text
from typing import Collection, List, Pattern, Type

import click
import psutil

import bento.five as five
import bento.parse_shebang as parse_shebang


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
    def drop_sig(signal, frame):
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
    click.secho(f"{indent}✘ {text}", fg="red", err=True)


def echo_warning(text: str, indent: str = "") -> None:
    click.secho(f"{indent}⚠ {text}", fg="yellow", err=True)


def echo_success(text: str, indent: str = "") -> None:
    click.secho(f"{indent}✔ {text}", fg="green", err=True)


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.exists(path):
            raise


@contextlib.contextmanager
def clean_path_on_failure(path):
    """Cleans up the directory on an exceptional failure."""
    try:
        yield
    except BaseException:
        if os.path.exists(path):
            rmtree(path)
        raise


@contextlib.contextmanager
def noop_context():
    yield


@contextlib.contextmanager
def tmpdir():
    """Contextmanager to create a temporary directory.  It will be cleaned up
    afterwards.
    """
    tempdir = tempfile.mkdtemp()
    try:
        yield tempdir
    finally:
        rmtree(tempdir)


def resource_bytesio(filename):
    return open_binary("pre_commit.resources", filename)


def resource_text(filename):
    return read_text("pre_commit.resources", filename)


def make_executable(filename):
    original_mode = os.stat(filename).st_mode
    os.chmod(filename, original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class CalledProcessError(RuntimeError):
    def __init__(self, returncode, cmd, expected_returncode, output=None):
        super(CalledProcessError, self).__init__(
            returncode, cmd, expected_returncode, output
        )
        self.returncode = returncode
        self.cmd = cmd
        self.expected_returncode = expected_returncode
        self.output = output

    def to_bytes(self):
        output = []
        for maybe_text in self.output:
            if maybe_text:
                output.append(
                    b"\n    " + five.to_bytes(maybe_text).replace(b"\n", b"\n    ")
                )
            else:
                output.append(b"(none)")

        return b"".join(
            (
                five.to_bytes(
                    "Command: {!r}\n"
                    "Return code: {}\n"
                    "Expected return code: {}\n".format(
                        self.cmd, self.returncode, self.expected_returncode
                    )
                ),
                b"Output: ",
                output[0],
                b"\n",
                b"Errors: ",
                output[1],
            )
        )

    def to_text(self):
        return self.to_bytes().decode("UTF-8")

    __bytes__ = to_bytes
    __str__ = to_text


def cmd_output(*cmd, **kwargs):
    retcode = kwargs.pop("retcode", 0)
    encoding = kwargs.pop("encoding", "UTF-8")

    popen_kwargs = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }

    # py2/py3 on windows are more strict about the types here
    cmd = tuple(five.n(arg) for arg in cmd)
    kwargs["env"] = {
        five.n(key): five.n(value) for key, value in kwargs.pop("env", {}).items()
    } or None

    try:
        cmd = parse_shebang.normalize_cmd(cmd)
    except parse_shebang.ExecutableNotFoundError as e:
        returncode, stdout, stderr = e.to_output()
    else:
        popen_kwargs.update(kwargs)
        proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore
        stdout, stderr = proc.communicate()
        returncode = proc.returncode
    if encoding is not None and stdout is not None:
        stdout = stdout.decode(encoding)
    if encoding is not None and stderr is not None:
        stderr = stderr.decode(encoding)

    if retcode is not None and retcode != returncode:
        raise CalledProcessError(returncode, cmd, retcode, output=(stdout, stderr))

    return returncode, stdout, stderr


def rmtree(path):
    """On windows, rmtree fails for readonly dirs."""

    def handle_remove_readonly(func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
            for p in (path, os.path.dirname(path)):
                os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
            func(path)
        else:
            raise

    shutil.rmtree(path, ignore_errors=False, onerror=handle_remove_readonly)


def parse_version(s):
    """poor man's version comparison"""
    return tuple(int(p) for p in s.split("."))
