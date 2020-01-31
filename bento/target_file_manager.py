from pathlib import Path
from typing import List

import attr
from pre_commit.git import zsplit

import bento.git
from bento.fignore import FileIgnore, Parser


@attr.s
class TargetFileManager:
    """
        Handles all logic related to knowing what files to run on. Only exposed API is get_target_files
    """

    _base_path = attr.ib(type=Path)
    _paths = attr.ib(type=List[Path])
    _staged = attr.ib(type=bool)
    _ignore_rules_file_path = attr.ib(type=Path)

    def _diffed_paths(self) -> List[Path]:
        repo = bento.git.repo()
        if not repo:
            return []

        # Will always be relative to repo root
        cmd = [
            "git",
            "diff",
            "--name-only",
            "--no-ext-diff",
            "-z",
            # Everything except for D
            "--diff-filter=ACMRTUXB",
            "--staged",
        ]
        result = repo.git.execute(cmd)
        str_paths = zsplit(result)

        # Resolve paths relative to cwd
        return [
            self._base_path
            / ((Path(repo.working_tree_dir) / p).resolve().relative_to(self._base_path))
            for p in str_paths
        ]

    def get_target_files(self) -> List[Path]:
        """
            Return list of all absolute paths to analyze
        """
        # resolve given paths relative to current working directory
        paths = [p.resolve() for p in self._paths]

        # If staged then only run on files that are different
        # and are a subpath of anything in input_paths
        if self._staged:
            targets = self._diffed_paths()
            paths = [
                diff_path
                for diff_path in targets
                # diff_path is a subpath of some element of input_paths
                if any(
                    (diff_path == path or path in diff_path.parents) for path in paths
                )
            ]

        # Filter out ignore rules, expand directories
        with self._ignore_rules_file_path.open() as ignore_lines:
            patterns = Parser(self._base_path, self._ignore_rules_file_path).parse(
                ignore_lines
            )

        file_ignore = FileIgnore(
            base_path=self._base_path, patterns=patterns, target_paths=paths
        )

        filtered: List[Path] = []
        for elem in file_ignore.entries():
            if elem.survives:
                filtered.append(elem.path)

        return filtered
