import json
import os
from typing import Dict, Optional, Set

from semantic_version import Version

from bento.tool import Tool


class JsTool(Tool):
    def _installed_version(self, package: str) -> Optional[Version]:
        """Gets the version of a package that was installed.

        Returns None if that package has not been installed."""
        package_json_path = os.path.join(
            self.base_path, "node_modules", package, "package.json"
        )
        try:
            with open(package_json_path) as f:
                package_json = json.load(f)
        except FileNotFoundError:
            return None
        if "version" in package_json:
            return Version(package_json["version"])
        else:
            return None

    def _npm_install(self, packages: Dict[str, Version]) -> None:
        """Runs npm install $package@^$version for each package."""
        print(f"Installing {packages}...")
        args = [f"{name}@^{version}" for name, version in packages.items()]
        self.exec(["npm", "install", "--save-dev"] + args, check=True)

    def _ensure_packages(self, packages: Dict[str, Version]) -> Set[str]:
        """Ensures that the given packages are installed.

        Returns the list of all packages that were installed.

        The argument maps package names to the minimum version. This is morally
        equivalent to a plain `npm install --save`, except it's faster in the
        case where all the packages are already installed.
        """
        to_install = {}
        for name, required_version in packages.items():
            installed = self._installed_version(name)
            if not (installed and installed >= required_version):
                to_install[name] = required_version
        if not to_install:
            return set()

        self._npm_install(to_install)
        return set(to_install)
