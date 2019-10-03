# Bento
Bento finds meaningful, novel bugs by automatically tailoring linters and static analysis on a per-project basis, letting you focus on writing code rather than configuring tools.

## Installation

Bento is supported on macOS Mojave (10.14) and Ubuntu 18.04+.
Bento requires Python version 3.6 or later and pip3.


### Installing Bento
Install Bento using:

`pip3 install r2c-bento`

## Usage

### Initialize Bento for a project:

In your project directory, run:

`bento init`

### Analyze your source code
To trigger Bento to analyze your project, run:

`bento check`

### Archive and baseline

The `archive` command whitelists all outstanding issues and saves them to the `.bento-whitelist.yml` file. This lets you continue coding with a clean slate. New issues introduced from this point forward will be reported by Bento until the next time you run the `archive` command.

Archive issues and get a clean slate by running:

`bento archive`

### Disable and enable individual checks
Enable a specific check by running:

`bento enable [OPTIONS] TOOL CHECK`, where:

* `TOOL` refers to the tool that includes the check, for example, `eslint`
*  `CHECK` refers to the label for the check you want to enable, for example `E211`

Disable a specific check by running:

`bento disable [OPTIONS] TOOL CHECK`, where:

* `TOOL` refers to the tool that includes the check, for example, `r2c.eslint`
*  `CHECK` refers to the name of the check you want to enable, for example `no-console`

## Help
Run `bento --help` to see available commands and options.

## Terms of service and privacy
Please refer to the [terms and privacy document](https://github.com/returntocorp/bento/blob/master/PRIVACY.md).

## License
Copyright (c) [r2c](https://r2c.dev ).
