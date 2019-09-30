#!/bin/bash
set -e

# regenerate requirements of bento
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run pipenv_to_requirements
pip3 install -e .
