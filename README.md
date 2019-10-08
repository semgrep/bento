# Bento
Bento finds meaningful, novel bugs by automatically tailoring linters and static analysis on a per-project basis, letting you focus on writing code rather than configuring tools.

## Installation

Bento is supported on macOS Mojave (10.14) and Ubuntu 18.04+.
Bento requires Python version 3.6 or later and pip3.


### Installing Bento
Bento is a command-line tool that is simple to install:

`pip3 install r2c-bento`

## Usage
The workflow for Bento is:  
1- Initialize Bento  
2- Run Bento checks on your source code  
3- Fix issues / archive unnecessary warning and errors  
4- Disable undesired checks  
5- Add Bento to git pre-commit hooks  
6- Add Bento to CI pipeline (ex: CircleCI)

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

* `TOOL` refers to the tool that includes the check, for example, `r2c.eslint`
*  `CHECK` refers to the label for the check you want to enable, for example `no-console`

Example: `bento enable r2c.eslint no-console`  

Disable a specific check by running:

`bento disable [OPTIONS] TOOL CHECK`, where:

* `TOOL` refers to the tool that includes the check, for example, `r2c.eslint`
*  `CHECK` refers to the name of the check you want to enable, for example `no-console`

## Demo
Here’s a short preview of Bento in action:

![Bento demo](bento-demo.gif)

## Help
Run `bento --help` to see available commands and options.

## Terms of service and privacy
Please refer to the [terms and privacy document](https://github.com/returntocorp/bento/blob/master/PRIVACY.md).

## License
Copyright (c) [r2c](https://r2c.dev ).
