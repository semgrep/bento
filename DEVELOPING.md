<h1 align="center" style="margin-top:0;">
  Bento
</h1>

<p align="center">
  <a href="https://pypi.org/project/bento-cli/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/bento-cli?style=flat-square&color=blue">
  </a>
  <a href="https://pypi.org/project/bento-cli/">
    <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/bento-cli?style=flat-square&color=green">
  </a>
</p>

See our public [README.md](https://github.com/returntocorp/bento) for Bento details.

# Developing

## Setup

Install pre-commit hooks:

```
brew install pre-commit
pre-commit install -f
```

Install pipenv:

```
pip3 install pipenv
```

Install bento dev dependencies:

```
pipenv install --dev
```

Setup git commit message template:

```
git config commit.template .gitmessage
```

## Testing

To run all tests:

```
pipenv run pytest
```

To build and run bento:

```
make
bento check
```

See [bento-core usage](https://returntocorp.quip.com/3K3gAxDYZIy6/Using-the-bento-core-repo) for more developer workflow details.
