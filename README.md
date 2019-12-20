<p align="center">
    <img src="https://raw.githubusercontent.com/returntocorp/bento/master/bento-logo.png" height="100" alt="Bento logo"/>
</p>
<h3 align="center">
  Find bugs delightfully fast without changing your workflow
</h3>

<p align="center">
  <a href="#installation">Installation</a>
  <span> · </span>
  <a href="#motivations">Motivations</a>
  <span> · </span>
  <a href="#usage">Usage</a>
  <span> · </span>
  <a href="#integrations">Integrations</a>
  <span> · </span>
  <a href="#bento-checks">Bento Checks</a>
  <span> · </span>
  <a href="#help-and-community">Help & Community</a>
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

Bento is a free bug-finding tool that runs locally when you commit code. It has speciality checks for common Python 3 web frameworks and OSS checks for JavaScript, TypeScript, Docker, and shell files.

- **Find bugs that matter.** Bento runs its [own checks](#bento-checks) and OSS tools to catch actual bugs. It never reports style-related issues and its checks are chosen based on performance across the PyPI and npm ecosystems.
- **Keep your workflow.** Unlike other tools you won’t have to fix existing bugs to adopt Bento. It takes 30 seconds to get started and coding again.
- **Go delightfully fast.** Bento runs its tools in parallel, not sequentially, on the code you’ve changed. Its jobs run entirely locally when you commit your code.

<p align="center">
    <img src="https://web-assets.r2c.dev/bento-demo.gif" width="100%" alt="Demonstrating Bento running in a terminal"/>
</p>

## Installation

```bash
$ pip3 install bento-cli
```

Bento requires Python 3.6+ and works on macOS Mojave (10.14) and Ubuntu 18.04+.

## Motivations

> See our [Bento introductory blog post](https://medium.com/@ievans/our-quest-to-make-world-class-security-and-bugfinding-available-to-all-developers-for-free-dce9eb7b06d0) to learn the full story.

r2c is on a quest to make world-class security and bugfinding available to all developers, for free. We’ve learned that most developers have never heard of—let alone tried—tools that find deep flaws in code: like Codenomicon, which found [Heartbleed](http://heartbleed.com/), or Zoncolan at Facebook, which finds more [top-severity security issues](https://cacm.acm.org/magazines/2019/8/238344-scaling-static-analyses-at-facebook/fulltext) than any human effort. These tools find severe issues and also save tons of time, identifying [hundreds of thousands of issues](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43322.pdf) before humans can. Bento is a step towards universal access to tools like these.

We’re also big proponents of opinionated tools like Black and Prettier. This has two implications: Bento ignores style-related issues and the bikeshedding that comes with them, and it ships with a curated set of checks that we believe are high signal and bug-worthy. See [Three things your linter shouldn’t tell you](https://blog.r2c.dev/posts/three-things-your-linter-shouldnt-tell-you/) for more details on our decision making process.

## Usage

### Getting Started

From the root directory of a project:

```bash
$ bento init
```

Bento is at its best when run automatically. See [Integrations](#integrations) for details.

### Upgrading

Run the following commands to upgrade Bento:

```bash
$ pip3 install --upgrade bento-cli
$ cd <PROJECT DIRECTORY>
$ rm -r .bento* && bento init
$ git add .bento* && git commit -m "Upgrade Bento configs"
```

### Command Line Options

```
$ bento --help

Usage: bento [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help             Show this message and exit.
  --version              Show current version bento.
  --base-path DIRECTORY  Path to the directory containing the code, as well as
                         the .bento.yml file.
  --agree                Automatically agree to terms of service.
  --email TEXT           Email address to use while running this command
                         without global configs e.g. in CI

Commands:
  archive       Adds all current findings to the whitelist.
  check         Checks for new findings.
  disable       Turn OFF a tool or check.
  enable        Turn ON a tool or check.
  init          Autodetects and installs tools.
  install-hook  Installs Bento as a git pre-commit hook.

  To get help for a specific command, run `bento COMMAND --help`
```

### Exit Codes

`bento check` may exit with the following exit codes:

- `0`: Bento ran successfully and found no errors
- `2`: Bento ran successfully and found issues in your code
- `3`: Bento or one of its underlying tools failed to run

## Integrations

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
$ pip3 install bento-cli && bento --version
$ bento --agree --email <YOUR_EMAIL> check
```

`bento check` will exit with a non-zero exit code if it finds issues in your code (see [Exit Codes](#exit-codes)). To suppress this behaviour you can pipe its output to `true`:

```bash
$ bento --agree --email <YOUR_EMAIL> check || true
```

Otherwise, address the issues or archive them with `bento archive`.

If you need help setting up Bento with another CI provider please [open an issue](https://github.com/returntocorp/bento/issues/new?template=feature_request.md). Documentation PRs welcome if you set up Bento with a CI provider that isn't documented here!

### Running Bento as a Git Hook

Bento can automatically analyze your staged files when `git commit` is run. Configured as a Git pre-commit hook, Bento ensures every commit to your project is vetted and that no new issues have been introduced to the codebase.

To install Bento as a Git hook:

```bash
$ bento install-hook
```

If Git hooks ever incorrectly block your commit, you can skip them by passing the `--no-verify` flag at commit-time (use this sparingly):

```bash
$ git commit --no-verify
```

Bento’s Git hook can save the round-trip time involved with fixing a failed build if you’re using [Bento in CI](#running-bento-in-ci).

## Bento Checks

Bento finds common security, correctness, and performance mistakes in projects containing Flask, Requests, and Boto 3. We’re inspired by tools that help ensure correct and safe framework use, like [eslint-plugin-react](https://github.com/yannickcr/eslint-plugin-react). Learn more about Bento’s speciality checks at [checks.bento.dev](https://checks.bento.dev/).

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
