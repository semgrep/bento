# Changelog

This project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2019-11-14

### Fixed

- Fixes a performance regression due to changes in metrics collection.

## [0.4.0] - 2019-11-11

### Changed

- We updated our [privacy policy](https://github.com/returntocorp/bento/commits/master/PRIVACY.md).
  - Notably, we collect email addresses to understand usage and communicate with users through product announcements, technical notices, updates, security alerts, and support messages.

### Added

- Added additional `r2c.click` tool for [Click](http://click.palletsprojects.com/) framework:

  - [flake8-click](https://pypi.org/project/flake8-click/) will be disabled by default.

- Added additional `r2c.flask` tool for [Flask](https://flask.palletsprojects.com/) framework:

  - [flake8-flask](https://pypi.org/project/flake8-flask/) will be disabled by default.

## [0.3.1] - 2019-11-08

### Fixed

- Fixed an issue where the tool would fail to install if a macOS user
  had installed `gcc` and then upgraded their OS.
- Fixed a compatibility issue for users with a pre-existing version
  of GitPython with version between 2.1.1 and 2.1.13.

## [0.3.0] - 2019-11-01

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

## [0.2.1] - 2019-10-29

### Fixed

- Quoted emails in git configuration do not break user registration.
- Removed files properly invalidate results cache.
- Python tools do not crawl `node_modules`.

## [0.2.0] - 2019-10-23

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
- Tool does not mangle .gitignore when that file lacks a trailing newline.
