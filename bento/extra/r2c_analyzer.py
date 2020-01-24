"""isort should skip this file since it does not
    play well with monkey patching

   isort:skip_file
"""

import logging
import json
import os
import pathlib
import shutil
import tempfile
from typing import Callable, Dict, List, Set, Iterable
from pathlib import Path

from semantic_version import Version
import r2c.lib.versioned_analyzer

from bento.extra.docker import get_docker_client
from bento.tool import JsonR


class MonkeyPatchVersionedAnalyzer(r2c.lib.versioned_analyzer.VersionedAnalyzer):
    @property
    def image_id(self) -> str:
        name = self.name.replace("/", "-")
        return f"bentoanalyzer/{name}:{self.version}"

    @classmethod
    def from_image_id(cls, image_id: str) -> "MonkeyPatchVersionedAnalyzer":
        name, version_str = image_id.split(":")
        name = name.split("/")[1]
        name = name.replace("-", "/", 1)
        return cls(r2c.lib.versioned_analyzer.AnalyzerName(name), Version(version_str))


# Monkey patch dockerhub image names instead of ECR
r2c.lib.versioned_analyzer.VersionedAnalyzer = (  # type: ignore
    MonkeyPatchVersionedAnalyzer
)

from r2c.lib.analyzer import Analyzer
from r2c.lib.constants import SPECIAL_ANALYZERS
from r2c.lib.filestore import (
    LocalFilesystemOutputStore,
    LocalJsonOutputStore,
    LocalLogStore,
    LocalStatsStore,
)
from r2c.lib.input import LocalCode
from r2c.lib.registry import AnalyzerDataJson, RegistryData
from r2c.lib.specified_analyzer import SpecifiedAnalyzer
from r2c.lib.util import get_tmp_dir
from r2c.lib.versioned_analyzer import AnalyzerName, VersionedAnalyzer

# TODO remove typing ignore after bumping r2c-lib version
TMP_DIR: str = get_tmp_dir()  # type: ignore
LOCAL_RUN_TMP_FOLDER = os.path.join(
    TMP_DIR, "bento", ""
)  # empty string to ensure trailing /
CONTAINER_MEMORY_LIMIT = "2G"


REGISTRY: Dict[str, AnalyzerDataJson] = {
    "public/source-code": {
        "versions": {
            "0.0.1": {
                "manifest": {
                    "_original_spec_version": "1.0.0",
                    "analyzer_name": "public/source-code",
                    "author_email": "analyzers@r2c.dev",
                    "author_name": "r2c built-in",
                    "dependencies": {},
                    "description": "Get a git repo at a specific commit.",
                    "deterministic": True,
                    "output": {"type": "filesystem"},
                    "readme": "# `public/source-code`\n\nAnalyzer for getting source code by using `git clone`. Expects its input to be\nJSON with `git_url` and `commit_hash` keys. Note that the `.git` directory will\nnot be included. If you want that, use `public/git-repo`.\n",
                    "spec_version": "1.1.0",
                    "type": "commit",
                    "version": "0.0.1",
                },
                "pending": False,
            }
        },
        "public": True,
    },
    "r2c/transpiler": {
        "versions": {
            "0.9.1": {
                "manifest": {
                    "analyzer_name": "r2c/transpiler",
                    "version": "0.9.1",
                    "spec_version": "1.2.0",
                    "dependencies": {"public/source-code": "*"},
                    "type": "commit",
                    "output": {"type": "both"},
                    "deterministic": True,
                },
                "pending": False,
            }
        },
        "public": False,
    },
    "r2c/checked-return": {
        "versions": {
            "0.1.11": {
                "manifest": {
                    "analyzer_name": "r2c/checked-return",
                    "author_email": "pad@returntocorp.com",
                    "author_name": "pad",
                    "dependencies": {"r2c/transpiler": "*"},
                    "deterministic": True,
                    "output": {"type": "json"},
                    "readme": "# Analyzer name: checked-return\n\n# Author name: pad\n\n# Description: TODO\n",
                    "spec_version": "1.2.0",
                    "type": "commit",
                    "version": "0.1.11",
                },
                "pending": False,
            }
        },
        "public": False,
    },
    "r2c/testonly-cat-output-json": {
        "versions": {
            "1.0.2": {
                "manifest": {
                    "analyzer_name": "r2c/testonly-cat-output-json",
                    "version": "1.0.2",
                    "spec_version": "1.1.0",
                    "dependencies": {"public/source-code": "*"},
                    "type": "commit",
                    "output": {"type": "json"},
                    "deterministic": True,
                    "_original_spec_version": "1.0.0",
                },
                "pending": False,
            }
        },
        "public": False,
    },
    "r2c/sgrep": {
        "versions": {
            "0.1.14": {
                "manifest": {
                    "analyzer_name": "r2c/sgrep",
                    "author_name": "pad",
                    "author_email": "pad@returntocorp.com",
                    "version": "0.1.14",
                    "spec_version": "1.2.0",
                    "dependencies": {"public/source-code": "*"},
                    "type": "commit",
                    "output": {"type": "json"},
                    "deterministic": True,
                    "readme": "# Analyzer name: sgrep\n\n# Author name: pad\n\n# Description: TODO\n",
                },
                "pending": False,
            }
        },
        "public": False,
    },
    "r2c/pyre-taint": {
        "versions": {
            "0.0.9": {
                "manifest": {
                    "analyzer_name": "r2c/pyre-taint",
                    "author_name": "pad",
                    "author_email": "pad@returntocorp.com",
                    "version": "0.0.9",
                    "spec_version": "1.2.0",
                    "dependencies": {"public/source-code": "*"},
                    "type": "commit",
                    "output": {"type": "json"},
                    "deterministic": True,
                    "readme": "# TODO\n",
                },
                "pending": False,
            }
        },
        "public": False,
    },
    "r2c/shellcheck": {
        "versions": {
            "0.0.1": {
                "manifest": {
                    "analyzer_name": "r2c/shellcheck",
                    "author_name": "brendon",
                    "author_email": "brendon.go@gmail.com",
                    "version": "0.0.1",
                    "spec_version": "1.2.0",
                    "dependencies": {"public/source-code": "*"},
                    "type": "commit",
                    "output": {"type": "json"},
                    "deterministic": True,
                    "readme": "# Analyzer name: shellcheck\n\n# Description\n\nr2c wrapper around koalaman/shellcheck https://github.com/koalaman/shellcheck\n",
                },
                "pending": False,
            }
        },
        "public": False,
    },
}


def _should_pull_analyzer(analyzer: SpecifiedAnalyzer) -> bool:
    """
        Returns True if the docker container for the analyzer is not
        available locally. Always returns False if the analyzer is a base
        analyzer (exists in SPECIAL_ANALYZERS)
    """

    if analyzer.versioned_analyzer.name in SPECIAL_ANALYZERS:
        return False

    client = get_docker_client()
    image_id = analyzer.versioned_analyzer.image_id
    return not any(i for i in client.images.list() if image_id in i.tags)


def prepull_analyzers(analyzer_name: str, version: Version) -> None:
    """
        Pulls all needed analyzers to run SPECIFIED_ANALYZER (i.e. dependencies)
    """

    specified_analyzer = SpecifiedAnalyzer(
        VersionedAnalyzer(AnalyzerName(analyzer_name), version)
    )
    registry = RegistryData.from_json(REGISTRY)

    deps = registry.sorted_deps(specified_analyzer)
    client = get_docker_client()
    for dep in deps:
        if _should_pull_analyzer(dep):
            client.images.pull(dep.versioned_analyzer.image_id)


def _ignore_files_factory(
    ignore_files: Set[Path], target_files: Set[str]
) -> Callable[[str, List[str]], List[str]]:
    """
        Takes list of absolute paths of files to ignore and returns
        a function compatible with what shutil.copytree's ignore_file expects.

        Assumes all elements of IGNORE_FILES and TARGET_FILES are absolute paths

        Said function used with copytree will copy all files under TARGET_FILES
        (i.e. if elem in target file is a file will include that file, if subdir
        then will include all dirs/files in said subdir) that are not in IGNORE_FILES

        Given the following directory tree:
        - root
            - unignore_dir
                - file.txt
            - ignored_dir
                - file.txt
            - ignored_file.txt
            - unignored_file.txt

        ----------------------------------------------------------------

        shutil.copytree called with
        ignore_files = set("root/ingored_dir", "root/ignored_file.txt")
        target_files = set("root/unignored_dir")

        will result in the following directory tree:
        - root
            - unignored_dir
                - file.txt

        ----------------------------------------------------------------

        shutil.copytree called with
        ignore_files = set("root/ingored_dir", "root/ignored_file.txt")
        target_files = set("root")
        will result in the following directory tree:
        - root
            - unignored_dir
                - file.txt
            - unignored_file.txt
    """

    def ignore_files_function(root: str, members: List[str]) -> List[str]:
        """
            shutil.copytree ignore_file expects a function that takes
            as argument the full path to a directory and a list
            of files/dirs in the directory and returns a list of files/dirs
            to ignore (a subset of the second argument).
        """
        rp = Path(root)
        return [
            path
            for path in members
            if rp / path in ignore_files
            or not any(
                # Suppose there is a file in a/b/c/d.py
                # LHS: If the target path is a/b/c/d.py we still want a/b to not be ignored to we keep traversing the tree.
                # RHS: If the target path is a we want a/b to be analyzed (so not ignored)
                r.startswith(f"{root}/{path}") or f"{root}/{path}".startswith(r)
                for r in target_files
            )
        ]

    return ignore_files_function


def _copy_local_input(
    analyzer: Analyzer,
    va: VersionedAnalyzer,
    analyzer_input: LocalCode,
    ignore_files: Set[Path],
    target_files: Set[str],
) -> None:
    """'Uploads' the local input as the output of the given analyzer.
    """
    code_dir = analyzer_input.code_dir
    with tempfile.TemporaryDirectory(prefix=LOCAL_RUN_TMP_FOLDER) as mount_folder:
        logging.debug(f"Created tempdir at {mount_folder}")
        os.mkdir(os.path.join(mount_folder, "output"))

        if not os.path.exists(code_dir):
            raise Exception("that code directory doesn't exist")

        output_fs_path = os.path.join(mount_folder, "output", "fs")

        # Note symlinks require different permissions on Windows. This is probably not compatible
        shutil.copytree(
            code_dir,
            output_fs_path,
            symlinks=True,
            ignore_dangling_symlinks=True,
            ignore=_ignore_files_factory(ignore_files, target_files),
        )

        # "upload" output using our LocalDir infra (actually just a copy)
        analyzer.upload_output(SpecifiedAnalyzer(va), analyzer_input, mount_folder)


def run_analyzer_on_local_code(
    analyzer_name: str,
    version: Version,
    base: Path,
    ignore_files: Set[Path],
    target_files: Iterable[str],
) -> JsonR:
    """Run an analyzer on a local folder.
    """
    get_docker_client()  # Ensures that docker is running

    specified_analyzer = SpecifiedAnalyzer(
        VersionedAnalyzer(AnalyzerName(analyzer_name), version)
    )
    registry = RegistryData.from_json(REGISTRY)

    json_output_store = LocalJsonOutputStore()
    filesystem_output_store = LocalFilesystemOutputStore()
    log_store = LocalLogStore()
    stats_store = LocalStatsStore()

    # All cacheing should be handled by bento
    json_output_store.delete_all()  # type: ignore
    filesystem_output_store.delete_all()  # type: ignore
    log_store.delete_all()  # type: ignore
    stats_store.delete_all()  # type: ignore

    pathlib.Path(LOCAL_RUN_TMP_FOLDER).mkdir(parents=True, exist_ok=True)

    analyzer = Analyzer(
        registry,
        json_output_store,
        filesystem_output_store,
        log_store,
        stats_store,
        workdir=LOCAL_RUN_TMP_FOLDER,
        timeout=0,  # Note Timeout relied on signaling which is not valid in multithreaded world
        memory_limit=CONTAINER_MEMORY_LIMIT,
    )

    # get all cloner versions from registry so we can copy the passed in code directory in place
    # of output for all versions of cloner
    fetchers = [
        sa
        for sa in registry.sorted_deps(specified_analyzer)
        if sa.versioned_analyzer.name in SPECIAL_ANALYZERS
    ]

    analyzer_input = LocalCode(str(base))
    for fetcher in fetchers:
        _copy_local_input(
            analyzer,
            fetcher.versioned_analyzer,
            analyzer_input,
            ignore_files,
            set(target_files),
        )

    analyzer.full_analyze_request(
        analyzer_input=analyzer_input,
        specified_analyzer=specified_analyzer,
        force=False,
    )

    # Get Final Output
    output = json_output_store.read(analyzer_input, specified_analyzer)
    if output is None:
        output = ""
    output_json = json.loads(output).get("results", [])

    # Cleanup state
    json_output_store.delete_all()  # type: ignore
    filesystem_output_store.delete_all()  # type: ignore
    log_store.delete_all()  # type: ignore
    stats_store.delete_all()  # type: ignore

    return output_json
