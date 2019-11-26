# Changelog

This project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.6.1](https://pypi.org/project/bento-cli/0.6.1/) - 2019-11-26

### Fixed

- Bento no longer completes initialization if it can't identify a project; this prevents
  confusing errors when subsequently running `bento check`.
- Pinned versions of all 3rd-party Python tools, so that remote package upgrades do not break
  Bento.
- Bento no longer crashes if a project path contains a space.

### Changed

- Results of `bento check` are now printed
  using the Clippy and histogram formatters (see "Added" section below) by default.
- The APIs to enable and disable a check are now `bento enable check [check]` and
  `bento disable check [check]`.
- The `r2c.flask` tool is now enabled by default. It finds best-practice and security bugs in
  code using the Python [Flask](https://www.palletsprojects.com/p/flask/) framework.
- Multiple formatters can now be used to display results from `bento check`. For example,
  `bento check -f stylish -f histo` will display results using the Stylish formatter,
  followed by display using a histogram formatter.
- Progress bars are not emitted to stderr if not a tty; this prevents progress-bar output from
  littering CI logs.
- Updated progress bar glyphs for readability on a wider range of terminal themes.
- Disabled `r2c.flake8` check `B001` by default, in favor of the (also included) `E722` check.

### Added

- Added `r2c.requests`, which finds best-practice and security bugs in code using the Python
  [Requests](https://2.python-requests.org/en/master/) framework. It is enabled by default.
- Added `r2c.sgrep`, a syntactically aware code search tool. It is _not_ enabled by default.
  To use it on a project, run `bento enable tool r2c.sgrep`. Note that Docker is required in
  order to use `r2c.sgrep`.
- All findings, including those previously archived, can now be viewed using
  `bento check --show-all`.
- Tools can now be enabled using `bento enable tool [tool_id]`. Available
  tools can be listed by running `bento enable tool --help` or using shell autocompletion.
  Tools can be disabled using `bento disable tool [tool_id]`.

## 0.6.0

Version 0.6.0 was not released.

## [0.5.0](https://pypi.org/project/bento-cli/0.5.0/) - 2019-11-18

### Fixed

- `r2c.eslint` now properly detects TypeScript imports.
- `r2c.eslint` now detects global node environments (e.g., `jest`),
  and properly resolves their global variables.

### Changed

- To better protect users' data, error messages are no longer reported to our backend.
- `.bentoignore` can now be configured to include patterns from other files; by default
  the contents of the project's `.gitignore` are included. For more information, please see the comments at
  the top of the generated `.bentoignore` file.
- Tab completion times reduced by approximately half.
- Disabled a number of `r2c.eslint` checks by default:
  - `arrow-parens`, as it conflicts with Prettier's default behavior.
  - TypeScript semicolon checking, which is stylistic.
  - `import/no-cycle` which takes 50% of tool runtime on moderately large code bases.
- `r2c.flake8 E306` disabled by default, as it is stylistic in nature.
- Runtime of `r2c.eslint` has been reduced by up to 30% for some projects.

### Added

- Added `r2c.shellcheck` tool for shell scripts. To enable, add `r2c.shellcheck` to the
  tools section of your `.bento.yml`. Note that this tool requires `docker` as a dependency.
- Added `r2c.hadolint` tool for Docker files. To enable, add `r2c.hadolint` to the
  tools section of your `.bento.yml`. Note that this tool requires `docker` to be installed in order to run.

## [0.4.1](https://pypi.org/project/bento-cli/0.4.1/) - 2019-11-14

### Fixed

- Fixes a performance regression due to changes in metrics collection.

## [0.4.0](https://pypi.org/project/bento-cli/0.4.0/) - 2019-11-11

### Changed

- We updated our [privacy policy](https://github.com/returntocorp/bento/commits/master/PRIVACY.md).
  - Notably, we collect email addresses to understand usage and communicate with users through product announcements, technical notices, updates, security alerts, and support messages.

### Added

- Added additional `r2c.click` tool for [Click](http://click.palletsprojects.com/) framework:

  - [flake8-click](https://pypi.org/project/flake8-click/) will be disabled by default.

- Added additional `r2c.flask` tool for [Flask](https://flask.palletsprojects.com/) framework:

  - [flake8-flask](https://pypi.org/project/flake8-flask/) will be disabled by default.

## [0.3.1](https://pypi.org/project/bento-cli/0.3.1/) - 2019-11-08

### Fixed

- Fixed an issue where the tool would fail to install if a macOS user
  had installed `gcc` and then upgraded their OS.
- Fixed a compatibility issue for users with a pre-existing version
  of GitPython with version between 2.1.1 and 2.1.13.

## [0.3.0](https://pypi.org/project/bento-cli/0.3.0/) - 2019-11-01

### Changed

- Bento can now be run from any subdirectory within a project.
- Updated the privacy and terms-of-service statement.

### Added

- File ignores are configurable via [git-style ignore patterns](https://git-scm.com/docs/gitignore) (include patterns
  are not supported). Patterns should be added to `.bentoignore`.

- Added additional checks to the `r2c.flake8` tool:

  - All checks from [flake8-bugbear](https://github.com/PyCQA/flake8-bugbear) (except for B009 and B010,
    which are stylistic in nature).
  - All checks from [flake8-builtins](https://github.com/gforcada/flake8-builtins).
  - All checks from [flake8-debugger](https://github.com/jbkahn/flake8-debugger).
  - All checks from [flake8-executable](https://github.com/xuhdev/flake8-executable).

- Clippy output formatting is now supported.
  - To enable, run: `bento check --formatter clippy`
  - Example output:

```
error: r2c.flake8.E113
   --> foo.py:6:5
    |
  6 |   return x
    |
    = note: unexpected indentation
```

- Autocompletion is now supported from both `bash` and `zsh`. To use:
  - In `bash`, run `echo -e '\neval "$(_BENTO_COMPLETE=source bento)"' >> ~/.bashrc`.
  - In `zsh`, run `echo -e '\neval "$(_BENTO_COMPLETE=source_zsh bento)"' >> ~/.zshrc`.

## [0.2.1](https://pypi.org/project/bento-cli/0.2.1/) - 2019-10-29

### Fixed

- Quoted emails in git configuration do not break user registration.
- Removed files properly invalidate results cache.
- Python tools do not crawl `node_modules`.

## [0.2.0](https://pypi.org/project/bento-cli/0.2.0/) - 2019-10-23

### Changed

- Results are cached between runs. This means that an immediate rerun of
  `bento` will be much faster.
- Broadened library compatibility, especially for common packages:
  - attrs from 18.2.0
  - packaging from 14.0
  - pre-commit from 1.0.0
- `r2c.eslint` ignores `.min.js` files. Bento should only report issues in code, not built artifacts.
- Telemetry endpoint uses `bento.r2c.dev`.

### Added

- Bento check will optionally run only on passed paths, using `bento check [path] ...`.
- Add `r2c.pyre` as a configurable tool. To enable, it must be manually configured in `.bento.yml`.
- Formatters can be specified with short names, and these appear in the help text. For example, `bento check --formatter json`.
- `bento` version is passed to telemetry backend.

### Fixed

- Tool does not crash if a git user does not have an email configured.
- Fixed a regression that caused progress bars to hang after first tool completed.
- Made fully compatible with Python 3.6.
- Tool does not mangle `.gitignore` when that file lacks a trailing newline.
