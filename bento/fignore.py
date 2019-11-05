import fnmatch
import logging
import os
import time
from pathlib import Path
from typing import Collection, Iterator, Set

import attr


@attr.s
class Entry(object):
    path = attr.ib(type=str)
    dir_entry = attr.ib(type=os.DirEntry)
    survives = attr.ib(type=bool)


@attr.s
class FileIgnore(object):
    base_path = attr.ib(type=Path)
    patterns = attr.ib(type=Set[str])
    _processed_patterns: Collection[str] = attr.ib(default=None, init=False)
    _walk_cache: Collection[Entry] = attr.ib(default=None, init=False)

    def __attrs_post_init__(self) -> None:
        self._process_patterns()
        self._init_cache()

    def _process_patterns(self) -> None:
        """
        Converts patterns in .gitignore syntax to a unified representation suitable
        for use with fnmatch.
        """

        def expand(p: str) -> str:
            """Convert a single pattern"""
            if p.rstrip("/").find("/") < 0:
                # Handles:
                #   file
                #   path/
                p = os.path.join("**", p)
            if p.startswith("./") or p.startswith("/"):
                # Handles:
                #   /relative/to/root
                #   ./relative/to/root
                p = p.lstrip(".").lstrip("/")
            if not p.startswith("**"):
                # Handles:
                #   path/to/absolute
                #   */to/absolute
                #   path/**/absolute
                p = os.path.join(self.base_path, p)
            return p

        self._processed_patterns = [expand(p) for p in self.patterns]

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
            if (not directories_only or e.is_dir()) and self._survives(root_path, e):
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
