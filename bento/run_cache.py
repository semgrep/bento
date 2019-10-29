import json
import logging
import os
from fnmatch import fnmatch
from typing import Iterable, List, Optional

import mmh3

from bento import __version__ as BENTO_VERSION
from bento.constants import LOCAL_RUN_CACHE


class RunCache(object):
    """
        Acts as a local cache for tool run output

        Different tools can be accessed concurrently, but cache access
        is not threadsafe if multiple threads access the same tool
    """

    @staticmethod
    def __cache_metadata_path(tool_id: str) -> str:
        """
            Returns name of file that cache results metadata for a given tool
        """
        return f"{LOCAL_RUN_CACHE}/{tool_id}-meta.json"

    @staticmethod
    def __cache_data_path(tool_id: str) -> str:
        """
            Returns name of file that cache results would be contained in
        """
        return f"{LOCAL_RUN_CACHE}/{tool_id}.data"

    @staticmethod
    def _modified_hash(paths: List[str]) -> str:
        """
        Returns a hash of the recursive mtime of a path.

        Any modification of a file within this tree (that does not match an ignore pattern)
        will change the hash.
        """
        # subdirectories to exclude
        # TODO: unify path ignore logic across bento
        exclude_dirs = [
            "**/.bento/*",
            "**/.git/*",
            "**/node_modules/*",
            "**/site-packages/*",
        ]
        exclude_files = {".bento-whitelist.yml", ".bento-baseline.yml", ".bento.yml"}

        def glob_match(root: str, exclude_dirs: Iterable[str]) -> bool:
            for ex in exclude_dirs:
                if fnmatch(f"{root}/", ex):
                    return True
            return False

        all_items = (
            os.path.join(root, f)
            for p in paths
            for root, dirs, files in os.walk(p)
            if not glob_match(root, exclude_dirs)
            for f in files
            if f not in exclude_files
        )
        h = 0
        for f in all_items:
            m = os.path.getmtime(f)
            h ^= mmh3.hash128(f"{f}:{m}")

        return format(h, "x")

    @staticmethod
    def __cleanup(tool_id: str) -> None:
        """
            Delete all state relevant for cacheing tool_id
        """
        cache_metadata_path = RunCache.__cache_metadata_path(tool_id)
        cache_data_path = RunCache.__cache_data_path(tool_id)

        # Silently delete file if exists
        # note that checking for file before deletion
        # has a TOCTOU race so will need a try-catch anyway
        try:
            os.remove(cache_metadata_path)
        except OSError:
            pass

        try:
            os.remove(cache_data_path)
        except OSError:
            pass

    @staticmethod
    def get(tool_id: str, paths: Iterable[str]) -> Optional[str]:
        """
            Returns stored run output if it exists in local run cache and the
            cache entry is still valid (files have not been modified since caching)

            Returns None if no such cache entry is found
        """
        cache_metadata_path = RunCache.__cache_metadata_path(tool_id)
        cache_data_path = RunCache.__cache_data_path(tool_id)

        if not (
            os.path.exists(cache_metadata_path) and os.path.exists(cache_data_path)
        ):
            RunCache.__cleanup(tool_id)
            return None

        with open(cache_metadata_path, "r") as file:
            try:
                metadata = json.load(file)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse tool {tool_id} cache metadata as json")
                logging.error(e.msg, e.doc, e.pos)
                RunCache.__cleanup(tool_id)
                return None

        cache_hash = metadata.get("hash")
        cache_paths = sorted(metadata.get("paths"))
        cache_bento_version = metadata.get("version")
        paths = sorted(paths)

        if (
            cache_paths != paths
            or cache_bento_version != BENTO_VERSION
            or cache_hash != RunCache._modified_hash(paths)
        ):
            logging.warning(f"Invalidating cache for {tool_id}")
            RunCache.__cleanup(tool_id)
            return None

        with open(cache_data_path) as file:
            raw_results = file.read()

        return raw_results

    @staticmethod
    def put(tool_id: str, paths: Iterable[str], raw_results: str) -> None:
        """
            Caches raw_results as the output of running TOOL_ID on PATHS

            Note that RunCache.get assumed paths is not None so should be changed
            if PATHS here is nullable
        """
        RunCache.__cleanup(tool_id)

        cache_metadata_path = RunCache.__cache_metadata_path(tool_id)
        cache_data_path = RunCache.__cache_data_path(tool_id)

        os.makedirs(os.path.dirname(cache_metadata_path), exist_ok=True)

        # Data should be written before metadata
        with open(cache_data_path, "w") as file:
            file.write(raw_results)

        # Convert paths to list so it is json serializable
        paths = sorted(paths)
        hash = RunCache._modified_hash(paths)

        metadata = {"paths": paths, "hash": hash, "version": BENTO_VERSION}

        with open(cache_metadata_path, "w") as file:
            json.dump(metadata, file)
