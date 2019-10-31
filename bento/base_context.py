import logging
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, Set, Union

import attr
import yaml

from bento.fignore import FileIgnore
from bento.run_cache import RunCache
from bento.util import echo_warning


def _clean_path(path: Union[str, Path]) -> Path:
    # The resolve here is important, since flake8 seems to have weird behavior
    # regarding finding unused imports if the path is not fully-resolved.
    return Path(path).resolve()


@attr.s
class BaseContext:
    # The path to the directory that contains the .bento dir and .bento.yml
    # file. Tools will also be run from here.
    base_path: Path = attr.ib(converter=_clean_path)
    is_init = attr.ib(type=bool, default=False)
    cache_path = attr.ib(type=Path, default=None)
    _config = attr.ib(type=Dict[str, Any], default=None)
    _resource_path = attr.ib(type=Path, default=None)
    _cache = attr.ib(type=RunCache, default=None, init=False)
    _ignores = attr.ib(type=FileIgnore, default=None, init=False)

    CONFIG_FILE: ClassVar[str] = ".bento.yml"
    RESOURCE_DIR: ClassVar[str] = ".bento"
    LOCAL_RUN_CACHE: ClassVar[str] = ".bento/cache"
    BASELINE_FILE_PATH: ClassVar[str] = ".bento-whitelist.yml"
    IGNORE_FILE_PATH: ClassVar[str] = ".bentoignore"

    @base_path.default
    def _find_base_path(self) -> Path:
        """Find the path to the nearest containing directory with bento config.

        This starts at the current directory, then recurses upwards looking for
        a directory with the necessary config file.

        The returned path is relative to the current working directory, so that
        when printed in log messages and such it looks readable.

        If one isn't found, returns the current working directory. This
        behavior is so that you can construct a Context in a directory that
        doesn't have Bento set up, then use the config_path and such to figure
        out where to do the initialization.

        """
        cwd = Path.cwd()
        for base_path in [cwd, *cwd.parents]:
            if (base_path / self.CONFIG_FILE).is_file():
                return base_path
        return cwd

    @property
    def config_path(self) -> Path:
        return self.base_path / self.CONFIG_FILE

    @property
    def resource_path(self) -> Path:
        if not self._resource_path:
            self._resource_path = self.base_path / self.RESOURCE_DIR
        return self._resource_path

    @property
    def baseline_file_path(self) -> Path:
        return self.base_path / self.BASELINE_FILE_PATH

    @property
    def ignore_file_path(self) -> Path:
        return self.base_path / self.IGNORE_FILE_PATH

    def pretty_path(self, path: Path) -> Path:
        try:
            return path.relative_to(self.base_path)
        except ValueError:
            return path

    def __attrs_post_init__(self) -> None:
        # We need to make sure the resource directory exists prior to creating the FileIgnore object,
        # otherwise it won't be detected in its directory scan.
        self.resource_path.mkdir(parents=True, exist_ok=True)
        self._ignores = FileIgnore(self.base_path, self._open_ignores())

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is None:
            self._config = self._open_config()
        return self._config

    @config.setter
    def config(self, config: Dict[str, Any]) -> None:
        self._write_config(config)
        self._config = config

    @property
    def file_ignores(self) -> FileIgnore:
        return self._ignores

    @property
    def cache(self) -> RunCache:
        if self._cache is None:
            cp = self.cache_path or (self.base_path / self.LOCAL_RUN_CACHE)
            self._cache = RunCache(cache_dir=cp, file_ignore=self.file_ignores)
        return self._cache

    def _open_config(self) -> Dict[str, Any]:
        """
        Opens this project's configuration file
        """
        logging.info(f"Loading bento configuration from {self.config_path}")
        with self.config_path.open() as yaml_file:
            return yaml.safe_load(yaml_file)

    def _write_config(self, config: Dict[str, Any]) -> None:
        """
        Overwrites this project's configuration file
        """
        logging.info(f"Writing bento configuration to {self.config_path}")
        with self.config_path.open("w") as yaml_file:
            yaml.safe_dump(config, yaml_file)

    def _open_ignores(self) -> Set[str]:
        """
        Opens this project's ignore file
        """
        ignore_file_path = self.ignore_file_path
        if not ignore_file_path.exists():
            if not self.is_init:
                echo_warning(
                    f"""'{self.ignore_file_path.relative_to(os.getcwd())}' not found; using default ignore patterns.
  Please run 'bento init' to configure a .bentoignore for your project.
"""
                )
            ignore_file_path = (
                Path(os.path.dirname(__file__)) / "configs" / ".bentoignore"
            )

        logging.info(
            f"Loading bento file ignores from {os.path.abspath(ignore_file_path)}"
        )

        def remove_comments(l: str) -> str:
            ix = l.find("#")
            if ix >= 0:
                return l[0:ix]
            else:
                return l

        with ignore_file_path.open() as ignore_file:
            stripped = (remove_comments(l).rstrip() for l in ignore_file)
            return {s for s in stripped if s}
