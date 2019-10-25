<h1 align="center">
  Bento
</h1>
<h3 align="center">
    Bento is a free toolkit that finds bugs that matter. It’s simple to install, configure, and adopt.
</h3>
![follow r2c](https://img.shields.io/twitter/follow/r2cdev?label=Follow%20r2cdev&style=social)

Bento is a free and opinionated toolkit for gradually adopting linters and program analysis into your codebase. You’ll be the bug squashing hero your team needs but (maybe) doesn’t deserve.

- **Find bugs that matter:** Bento automatically enables relevant rules based on your dependencies and frameworks and it will never report style-related issues. Avoid painstakingly configuring your tools.
- **Get started immediately:** By archiving existing issues and allowing you to adopt incrementally, Bento doesn’t force you to fix all your preexisting issues today. Set them aside to address when it makes sense for your project.
- **Go fast:** Bento installs in 5 seconds and self-configures in less than 30. Tools check your code in parallel, not sequentially.

Bento includes checks written by [r2c](https://r2c.dev/) and curated from [Bandit](https://pypi.org/project/bandit/),[ESLint](https://eslint.org/), [Flake8](https://pypi.org/project/flake8/), and their plugins.


## Installation

```shell
$ pip3 install bento-cli
```

Bento is for JavaScript, TypeScript, and Python projects. It requires Python 3.6+ and works on macOS Mojave (10.14) and Ubuntu 18.04+.

## Usage

To get started right away with sensible defaults:

```shell
$ bento init && bento check
```

To set aside preexisting results so you only see issues in new code:

```shell
$ bento archive
```

Bento really sings when you run it automatically in your editor, as a commit hook (`bento install-hook`), or in CI. See [Integrating Bento Into Your Workflow]() to get the most out of it and think less.

### Archive outstanding issues

The `archive` command whitelists outstanding issues to fix later. This lets you continue coding with a clean slate without having to address all your tech debt as soon as you adopt a new tool. New issues introduced from this point forward will be reported by Bento until the next time you run the `archive` command.

Archive issues by running:

```bash
bento archive
```

### Disable and enable individual checks
Enable/disable a specific check by running:

```
bento enable [OPTIONS] TOOL CHECK
```
or
```
bento disable [OPTIONS] TOOL CHECK
```
where:

* `TOOL` refers to the tool that includes the check, for example, `r2c.eslint`
*  `CHECK` refers to the label for the check you want to enable, for example `no-console`

Example: 

```
bento enable r2c.eslint no-console
```
You can find the tool and check names in the output of `bento check`. Bento currently supports the following tools:

| Language   | Supported Tools |
|------------|-----------------|
| Python     | Bandit, Flake8  |
| JavaScript | ESLint          |

If there are tools you'd like us to add, please let us know by [creating an issue](https://github.com/returntocorp/bento/issues/new?assignees=&labels=feature-request&template=feature_request.md&title=).

### Install Bento as a pre-commit hook
To install bento as a pre-commit hook, simply run:
```bash
bento install-hook
```

## Demo
Here’s a short preview of Bento in action:

![Bento demo](bento-demo.gif)

## Help and Community
Need help or want to share feedback about Bento? Reach out to us at [support@r2c.dev](mailto:support@r2c.dev). The r2c team wants to hear from you!

You can also join the Bento channel in our [community Slack](https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA) to receive and give support, talk with other users, and share things about Bento. 

## Terms of service and privacy
Please refer to the [terms and privacy document](https://github.com/returntocorp/bento/blob/master/PRIVACY.md).

## License
Copyright (c) [r2c](https://r2c.dev ).

![r2c logo](https://r2c.dev/r2c-logo-silhouette.png?gh)
