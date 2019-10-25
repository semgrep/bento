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

Bento includes checks written by [r2c](https://r2c.dev/) and curated from [Bandit](https://pypi.org/project/bandit/), [ESLint](https://eslint.org/), [Flake8](https://pypi.org/project/flake8/), and their plugins.

<p align="center">
    <img src="bento-demo.gif" width="50%" height="50%"/>
</p>

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

## Command Line Options
```shell
$ bento --help

Usage: bento [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show current Bento version.
  --agree    Automatically agree to terms of service.
  --help     Show this message and exit.

Commands:
  archive       Adds all current findings to the whitelist.
  check         Checks for new findings.
  disable       Disables a check.
  enable        Enables a check.
  init          Autodetects and installs tools.
  install-hook  Installs Bento as a git pre-commit hook.
```


## Help and Community
- Need help or want to share feedback? Reach out to us at [support@r2c.dev](mailto:support@r2c.dev). We’d love to hear from you! 💌
- Join #bento in our [community Slack](https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA) for support, to talk with other users, and share feedback. 🤝
- We’re fortunate to benefit from the contributions and work of the open source community and great projects such as [Bandit](https://pypi.org/project/bandit/), [ESLint](https://eslint.org/), [Flake8](https://pypi.org/project/flake8/), and their plugins. 🙏

## License and Legal
Please refer to the [terms and privacy document](https://github.com/returntocorp/bento/blob/master/PRIVACY.md).

Copyright (c) [r2c](https://r2c.dev ).

![r2c logo](https://r2c.dev/r2c-logo-silhouette.png?gh)
