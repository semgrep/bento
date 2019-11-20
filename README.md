<p align="center">
    <img src="https://raw.githubusercontent.com/returntocorp/bento/master/bento-logo.png" height="100" alt="Bento logo"/>
</p>
<h1 align="center" style="margin-top:0;"></h1>

<br/>
<h3 align="center">
    Free program analysis focused on bugs that matter to you.
</h3>
<p align="center">
Install, configure, and adopt Bento in seconds. Runs 100% locally.
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
  <a href="https://twitter.com/intent/follow?screen_name=r2cdev">
    <img src="https://img.shields.io/twitter/follow/r2cdev?label=Follow%20r2cdev&style=social&color=blue" alt="Follow @r2cdev" />
  </a>
</p>

<h3 align="center">
  <a href="#installation">Installation</a>
  <span> · </span>
  <a href="#motivations">Motivations</a>
  <span> · </span>
  <a href="#usage">Usage</a>
  <span> · </span>
  <a href="#running-bento-in-ci">CI/CD</a>
  <span> · </span>
  <a href="#help-and-community">Help & Community</a>
</h3>

Bento is a free and opinionated toolkit for gradually adopting linters[¹](https://en.wikipedia.org/wiki/Lint_(software)) and program analysis[²](https://en.wikipedia.org/wiki/Program_analysis) in your codebase. Be the bug-squashing advocate your team needs but (maybe) doesn’t deserve.

- **Find bugs that matter.** Bento automatically enables and configures relevant analysis based on your dependencies and frameworks, and it will [never report style-related issues](https://blog.r2c.dev/posts/three-things-your-linter-shouldnt-tell-you/). You won’t painstakingly configure your tooling.
- **Get started immediately.** Bento doesn’t force you to fix all your preexisting issues today. Instead, you can archive them and address them incrementally when it makes sense for your project.
- **Go fast.** Bento installs in 5 seconds and self-configures in less than 30. Its tools check your code in parallel, not sequentially.

Bento includes checks written by [r2c](https://r2c.dev/) and curated from [Bandit](https://pypi.org/project/bandit/), [ESLint](https://eslint.org/), [Flake8](https://pypi.org/project/flake8/), and their plugins. It runs on your local machine and never sends your code anywhere or to anyone.

<p align="center">
    <img src="https://web-assets.r2c.dev/bento-demo.gif" width="100%" alt="Demonstrating Bento running in a terminal"/>
</p>

## Installation
```bash
$ pip3 install bento-cli
```

Bento is for JavaScript, TypeScript, and Python 3 projects. It requires Python 3.6+ and works on macOS Mojave (10.14) and Ubuntu 18.04+.

## Motivations
> See our [Bento introductory blog post](https://medium.com/@ievans/our-quest-to-make-world-class-security-and-bugfinding-available-to-all-developers-for-free-dce9eb7b06d0) to learn the full story.

r2c is on a quest to make world-class security and bugfinding available to all developers, for free. We’ve learned that most developers have never heard of—let alone tried—tools that find deep flaws in code: like Codenomicon, which found [Heartbleed](http://heartbleed.com/), or Zoncolan at Facebook, which finds more [top-severity security issues](https://cacm.acm.org/magazines/2019/8/238344-scaling-static-analyses-at-facebook/fulltext) than any human effort. These tools find severe issues and also save tons of time, identifying [hundreds of thousands of issues](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43322.pdf) before humans can. Bento is a step towards universal access to tools like these.

We’re also big proponents of opinionated tools like Black and Prettier. This has two implications: Bento ignores style-related issues and the bikeshedding that comes with them, and it ships with a curated set of checks that we believe are high signal and bug-worthy. See [Three things your linter shouldn’t tell you](https://blog.r2c.dev/posts/three-things-your-linter-shouldnt-tell-you/) for more details on our decision making process.

## Usage
To get started right away with sensible defaults:

```bash
$ bento init && bento check
```

To set aside preexisting results so you only see issues in new code:

```bash
$ bento archive
```

Bento is at its best when run automatically as a Git pre-commit hook (i.e. `bento install-hook`) or as part of CI.

### Command Line Options
```bash
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

### Exit Codes
`bento check` may exit with the following exit codes: 
- `0`: Bento ran successfully and found no errors
- `2`: Bento ran successfully and found issues in your code
- `3`: Bento or one of its underlying tools failed to run

### Running Bento in CI
If you use CircleCI, add the following job:

```yaml
version: 2.1

jobs:
    bentoCheck:
    executor: circleci/python:3.7.4-stretch-node
    steps:
      - checkout
      - run:
          name: "Install Bento"
          command: pip3 install bento-cli && bento --version
      - run:
          name: "Run Bento check"
          command: bento --agree --email <YOUR_EMAIL> check
```

Otherwise, you can simply install and run Bento in CI with the following commands:

```bash
pip3 install bento-cli && bento --version
bento --agree --email <YOUR_EMAIL> check
```

`bento check` will exit with a non-zero exit code if it finds issues in your code (see [Exit Codes](#exit-codes)). You can run `bento --agree --email <YOUR_EMAIL> check || true` if you'd like to prevent Bento from blocking your build. Otherwise, address the issues or unblock yourself by running `bento archive`.

Please [open an issue](https://github.com/returntocorp/bento/issues/new?template=feature_request.md) if you need help setting up Bento with another CI provider. If you set up Bento with your provider of choice, we’d appreciate a PR to add instructions here! 

## Help and Community
Need help or want to share feedback? We’d love to hear from you!

- Email us at [support@r2c.dev](mailto:support@r2c.dev)
- Join #bento in our [community Slack](https://join.slack.com/t/r2c-community/shared_invite/enQtNjU0NDYzMjAwODY4LWE3NTg1MGNhYTAwMzk5ZGRhMjQ2MzVhNGJiZjI1ZWQ0NjQ2YWI4ZGY3OGViMGJjNzA4ODQ3MjEzOWExNjZlNTA)
- [File an issue](https://github.com/returntocorp/bento/issues/new?assignees=&labels=bug&template=bug_report.md&title=) or [submit a feature request](https://github.com/returntocorp/bento/issues/new?assignees=&labels=feature-request&template=feature_request.md&title=) directly on GitHub &mdash; we welcome them all!

We’re constantly shipping new features and improvements. 

- [Sign up for the Bento newsletter](http://eepurl.com/gDeFvL) &mdash; we promise not to spam and you can unsubscribe at any time
- See past announcements, releases, and issues [here](https://us18.campaign-archive.com/home/?u=ee2dc8f77e27d3739cf4df9ef&id=d13f5e938e)

We’re fortunate to benefit from the contributions of the open source community and great projects such as [Bandit](https://pypi.org/project/bandit/), [ESLint](https://eslint.org/), [Flake8](https://pypi.org/project/flake8/), and their plugins. 🙏

## License and Legal
Please refer to the [terms and privacy document](https://github.com/returntocorp/bento/blob/master/PRIVACY.md).

</br>
</br>
<p align="center">
    <img src="https://web-assets.r2c.dev/r2c-logo-silhouette.png?gh" height="24" alt="r2c logo"/>
</p>
<p align="center">
    Copyright (c) <a href="https://r2c.dev">r2c</a>.
</p>
