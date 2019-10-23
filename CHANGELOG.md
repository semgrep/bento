# Changelog

This project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2019-10-23

### Changed

- Results are cached between runs. This means that an immediate rerun of
  `bento` will take minimal time.
- Broadened library compatibility, especially for common packages:
  - attrs from 18.2.0
  - packaging from 14.0
  - pre-commit from 1.0.0
- `r2c.eslint` ignores `.min.js` files.
- Telemetry endpoint uses bento.r2c.dev.

### Added

- Bento check will optionally run only on passed paths, using `bento check [path] ...`.
- Add `r2c.pyre` as a configurable tool. To enable, it must be manually configured in `.bento.yml`.
- Formatters can be specified with short names, and these appear in the help. For example, `bento check --formatter json`.
- `bento` version is passed to telemetry backend.

### Fixed

- Tool does not crash if a git user does not have an email configured.
- Fixed a regression that caused progress bars to hang after first tool completed.
- Made fully compatible with Python 3.6.
