import fnmatch
import logging
import os
import re
import time
from pathlib import Path
from typing import Collection, Iterable, Iterator, Set, TextIO

import attr

from bento.util import echo_warning

IGNORE_ESCAPE_CHARACTERS = {":", "\\", "[", "]", "!"}
CONTROL_REGEX = re.compile(r"(?!<\\):")  # Matches unescaped colons
MULTI_CHAR_REGEX = re.compile(
    r"(?!<\\)\[.*(?!<\\)\]"
)  # Matches anything in unescaped brackets


@attr.s
class Entry(object):
    path = attr.ib(type=str)
    dir_entry = attr.ib(type=os.DirEntry)
    survives = attr.ib(type=bool)


@attr.s
class FileIgnore(object):
    base_path = attr.ib(type=Path)
    patterns = attr.ib(type=Set[str])
    _processed_patterns = attr.ib(type=Set[str], init=False)
    _walk_cache: Collection[Entry] = attr.ib(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        self._processed_patterns = Processor(self.base_path).process(self.patterns)
        self._init_cache()

    def _survives(self, base_path: str, entry: os.DirEntry) -> bool:
        """
        Determines if a single file entry survives the ignore filter.
        """
        for p in self._processed_patterns:
            if (
                entry.is_dir()
                and p.endswith("/")
                and fnmatch.fnmatch(entry.path, p[:-1])
            ):
                return False
            if fnmatch.fnmatch(entry.path, p):
                return False
        return True

    def _walk(
        self, this_path: str, root_path: str, directories_only: bool = True
    ) -> Iterator[Entry]:
        """
        Walks path, returning an Entry iterator for each item.

        If an item is not ignored, it is traversed recursively. Traversal stops on
        ignored items.

        Recalculates on every call.
        """
        for e in os.scandir(this_path):
            if e.is_symlink():
                continue
            elif (not directories_only or e.is_dir()) and self._survives(root_path, e):
                filename = os.path.join(this_path, e.name)
                yield Entry(filename, e, True)
                if e.is_dir():
                    before = time.time()
                    for ee in self._walk(e.path, root_path, directories_only):
                        yield ee
                    logging.debug(f"Scanned {filename} in {time.time() - before} s")
            else:
                filename = os.path.join(this_path, e.name)
                yield Entry(filename, e, False)

    def _init_cache(self) -> None:
        pretty_patterns = "\n".join(self.patterns)
        logging.info(f"Ignored patterns are:\n{pretty_patterns}")
        before = time.time()
        self._walk_cache = list(
            self._walk(str(self.base_path), str(self.base_path), directories_only=False)
        )
        logging.info(f"Loaded file ignore cache in {time.time() - before} s.")

    def entries(self) -> Collection[Entry]:
        """
        Returns all files that are not ignored, relative to the base path.
        """
        return self._walk_cache


@attr.s(auto_attribs=True)
class Parser(object):
    r"""
    A parser for bentoignore syntax.

    bentoignore syntax mirrors gitignore syntax, with the following modifications:
    - "Include" patterns (lines starting with "!") are not supported.
    - "Character range" patterns (lines including a collection of characters inside brackets) are not supported.
    - An ":include ..." directive is added, which allows another file to be included in the ignore pattern list;
      typically this included file would be the project .gitignore. No attempt at cycle detection is made.
    - Any line beginning with a colon, but not ":include ", will raise a ValueError.
    - "\:" is added to escape leading colons.

    Unsupported patterns are silently removed from the pattern list (this is done so that gitignore files may be
    included without raising errors), although the removal will be logged.

    Unfortunately there's no available parser for gitignore syntax in python, so we have
    to make our own. The syntax is simple enough that we can just roll our own parser, so
    I deliberately skip using a parser generator or combinator library, which would either need to
    parse on a character-by-character basis or make use of a large number of regex scans.

    The parser steps are, for each line in the input stream:
    1. Remove comments
    2. Remove unsupported gitignore syntax
    3. Expand directives

    The end result of this parsing is a set of human-readable patterns corresponding to gitignore syntax.
    To use these patterns with fnmatch, however, a final postprocessing step is needed, achieved by calling
    Processor.process().

    :param base_path:   The path relative to which :include directives should be evaluated
    :param ignore_path: The path of the file being parsed (for logging only)
    """

    # Parser steps are each represented as Generators. This allows us to chain
    # steps, whether the step is a transformation, a filter, an expansion, or any combination thereof.

    base_path: Path
    ignore_path: Path

    @staticmethod
    def remove_comments(line: str) -> Iterator[str]:
        """Removes comments from a line, as well as trailing whitespace"""
        cleaned = line
        ix = line.find("#")
        if ix >= 0:
            cleaned = line[0:ix]
        yield cleaned.rstrip()

    @staticmethod
    def filter_supported(line: str) -> Iterator[str]:
        """Remove unsupported gitignore patterns"""
        if not line:
            pass
        elif line.startswith("!") or MULTI_CHAR_REGEX.search(line):
            logging.warning(f"Skipping unsupported gitignore pattern '{line}'")
        else:
            yield line

    def expand_directives(self, line: str) -> Iterable[str]:
        """Load :include files"""
        if line.startswith(":include "):
            include_path = self.base_path / line[9:]
            with include_path.open() as include_lines:
                sub_base = include_path.parent.resolve()
                sub_parser = Parser(sub_base, include_path)
                return sub_parser.parse(include_lines)
        elif CONTROL_REGEX.match(line):
            raise ValueError(
                f"Unknown ignore directive in {self.ignore_path}: '{line}'"
            )
        else:
            return (line for _ in range(1))

    def parse(self, stream: TextIO) -> Set[str]:
        """Performs parsing of an input stream"""
        return {
            pattern
            for line in stream
            for no_comments in self.remove_comments(line)
            for supported in self.filter_supported(no_comments)
            for pattern in self.expand_directives(supported)
        }


@attr.s(auto_attribs=True)
class Processor(object):
    """
    A post-processor for parsed bentoignore files.

    The postprocessor is responsible for converting the parser's intermediate representation to a set of
    patterns compatible with fnmatch. The steps are:
    1. Unescape escape characters
    2. Convert gitignore patterns into fnmatch patterns
    """

    # Per Parser, each Processor step is represented as a Generator.

    base_path: Path

    @staticmethod
    def unescape(line: str) -> Iterator[str]:
        """Expands escape characters"""
        out = ""
        is_escape = False
        for c in line:
            if is_escape:
                if c in IGNORE_ESCAPE_CHARACTERS:
                    out += c
                    is_escape = False
                else:
                    raise ValueError(
                        f"Unknown escape sequence '\\{c}' in ignore pattern '{line}'"
                    )
            elif c == "\\":
                is_escape = True
            else:
                out += c
        yield out

    def to_fnmatch(self, pat: str) -> Iterator[str]:
        """Convert a single pattern from gitignore to fnmatch syntax"""
        if pat.rstrip("/").find("/") < 0:
            # Handles:
            #   file
            #   path/
            pat = os.path.join("**", pat)
        if pat.startswith("./") or pat.startswith("/"):
            # Handles:
            #   /relative/to/root
            #   ./relative/to/root
            pat = pat.lstrip(".").lstrip("/")
        if not pat.startswith("**"):
            # Handles:
            #   path/to/absolute
            #   */to/absolute
            #   path/**/absolute
            pat = os.path.join(self.base_path, pat)
        yield pat

    def process(self, pre: Iterable[str]) -> Set[str]:
        """Post-processes an intermediate representation"""
        return {
            pattern
            for pat in pre
            for unescaped in self.unescape(pat)
            for pattern in self.to_fnmatch(unescaped)
        }


def open_ignores(
    base_path: Path, ignore_path: Path, is_init: bool = False
) -> FileIgnore:
    """
    Opens this project's ignore file
    """
    if not ignore_path.exists():
        if not is_init:
            echo_warning(
                f"""'{os.path.relpath(ignore_path, os.getcwd())}' not found; using default ignore patterns.
Please run 'bento init' to configure a .bentoignore for your project.
"""
            )
        ignore_path = Path(os.path.dirname(__file__)) / "configs" / ".bentoignore"

    logging.info(f"Loading bento file ignores from {os.path.abspath(ignore_path)}")

    with ignore_path.open() as ignore_lines:
        patterns = Parser(base_path, ignore_path).parse(ignore_lines)
        return FileIgnore(base_path=base_path, patterns=patterns)
