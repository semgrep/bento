import json
import os
import subprocess
from typing import Dict, Optional, Set

from semantic_version import NpmSpec, Version

from bento.error import NodeError
from bento.tool import Tool

NODE_VERSION_RANGE = NpmSpec("^8.10.0 || ^10.13.0 || >=11.10.1")


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
        uses_yarn = os.path.exists(os.path.join(self.base_path, "yarn.lock"))
        args = [f"{name}@^{version}" for name, version in packages.items()]
        if uses_yarn:
            # If yarn is using nested project, we still want to install in workspace root
            cmd = ["yarn", "add", "--dev", "--ignore-workspace-root-check"]
        else:
            cmd = ["npm", "install", "--save-dev"]
        self.execute(cmd + args, check=True)

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

    def _ensure_node_version(self) -> None:
        """Ensures that Node.js version installed on the system is compatible with ESLint v6
        per https://github.com/eslint/eslint/blob/master/docs/user-guide/migrating-to-6.0.0.md#-nodejs-6-is-no-longer-supported
        Suppored Node.js version  ^8.10.0 || ^10.13.0 || >=11.10.1
        """
        version = self.execute(
            ["node", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        node_version = version.stdout.rstrip().strip("v")
        if version.returncode > 0 or not NODE_VERSION_RANGE.match(
            Version(node_version)
        ):
            raise NodeError(
                f"Node.js is not installed, or its version is not >8.10.0, >10.13.0, or >=11.10.1 (found {node_version})."
            )
