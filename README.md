<h1 align="center" style="margin-top:0;">
  Bento
</h1>
<h3 align="center">
    Install, configure, and adopt in seconds.
</h3>
<p align="center">
Bento is a free program analysis toolkit that finds bugs that matter to you.
</p>
<p align="center">
  <a href="https://pypi.org/project/bento-cli/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/bento-cli?style=flat-square&color=blue">
  </a>
  <a href="https://pypi.org/project/bento-cli/">
    <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/bento-cli?style=flat-square&color=green">
  </a>
  <a href="https://github.com/returntocorp/bento/issues/new/choose">
    <img src="https://img.shields.io/badge/issues-welcome-green?style=flat-square" alt="Issues welcome!" />
  </a>
  <a href="https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA">
    <img src="https://img.shields.io/badge/chat-on%20slack-blue?style=flat-square">
  </a>
  <a href="https://twitter.com/intent/follow?screen_name=r2cdev">
    <img src="https://img.shields.io/twitter/follow/r2cdev?label=Follow%20r2cdev&style=social&color=blue" alt="Follow @r2cdev" />
  </a>
</p>
<br>
<br>

Bento is a free and opinionated toolkit for gradually adopting linters[¹](https://en.wikipedia.org/wiki/Lint_(software)) and program analysis[²](https://en.wikipedia.org/wiki/Program_analysis) in your codebase. You’ll be the bug squashing hero your team needs but (maybe) doesn’t deserve.

- **Find bugs that matter.** Bento automatically enables and configures relevant analysis based on your dependencies and frameworks, and it will never report style-related issues. You won't painstakingly configure your tooling.
- **Get started immediately.** Bento doesn’t force you to fix all your preexisting issues today. Instead, you can archive them and address them incrementally when it makes sense for your project.
- **Go fast.** Bento installs in 5 seconds and self-configures in less than 30. Its tools check your code in parallel, not sequentially.

Bento includes checks written by [r2c](https://r2c.dev/) and curated from [Bandit](https://pypi.org/project/bandit/), [ESLint](https://eslint.org/), [Flake8](https://pypi.org/project/flake8/), and their plugins.

<p align="center">
    <img src="bento-demo.gif" width="70%" alt="gif demonstrating Bento running in a terminal"/>
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

</br>
</br>
<p align="center">
    <img src="https://r2c.dev/r2c-logo-silhouette.png?gh" height="24" alt="r2c logo"/>
</p>
<p align="center">
    Copyright (c) <a href="https://r2c.dev">r2c</a>.
</p>
