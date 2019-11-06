import subprocess
import tempfile
from pathlib import Path
from typing import Any, List, Union

import yaml

import bento.constants

Expectation = Union[str, List[str]]

BENTO_REPO_ROOT = str(Path(__file__).parent.parent.parent)


def match_expected(output: str, expected: Expectation, test_identifier: str) -> None:
    """Checks that OUTPUT matches EXPECTED

    If EXPECTED is a string then checks that OUTPUT and EXPECTED are exact
    matches ignoring trailing whitespace

    If EXPECTED is a List then checks that every string in EXPECTED is contained in OUTPUT
    """
    if isinstance(expected, str):
        assert output.strip() == expected.strip(), test_identifier
    else:
        for elem in expected:
            assert elem.strip() in output, test_identifier


def check_command(step: Any, pwd: str, target: str) -> None:
    """Runs COMMAND in with cwd=PWD and checks that the returncode, stdout, and stderr
    match their respective expected values.
    """
    command = step["command"]

    expected_returncode = step.get("returncode")
    expected_out = step.get("expected_out")
    expected_err = step.get("expected_err")

    # Read files if any
    if isinstance(expected_out, dict):
        with open(f"tests/acceptance/{target}/{expected_out['file']}") as file:
            expected_out = file.read()
    if isinstance(expected_err, dict):
        with open(f"tests/acceptance/{target}/{expected_err['file']}") as file:
            expected_err = file.read()

    test_identifier = f"Target:{target} Step:{step['name']}"
    substituted = [
        part.replace("__BENTO_REPO_ROOT__", BENTO_REPO_ROOT) for part in command
    ]
    if substituted[0] == "bento":
        substituted = [
            "bento",
            "--email",
            bento.constants.QA_TEST_EMAIL_ADDRESS,
        ] + substituted[1:]

    runned = subprocess.run(
        substituted,
        # Note that we can't use BENTO_BASE_PATH since the acceptance tests
        # depend on hook installation, which uses the working directory.
        cwd=pwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    if expected_returncode is not None:
        assert runned.returncode == expected_returncode, test_identifier
    if expected_out is not None:
        match_expected(runned.stdout, expected_out, f"{test_identifier}: stdout")
    if expected_err is not None:
        match_expected(runned.stderr, expected_err, f"{test_identifier}: stderr")


def run_repo(target: str) -> None:
    with open(f"tests/acceptance/{target}/commands.yaml") as file:
        info = yaml.safe_load(file)

    target_repo = info["target_repo"]
    target_hash = info["target_hash"]
    steps = info["steps"]

    with tempfile.TemporaryDirectory() as target_dir:

        subprocess.run(
            ["git", "clone", target_repo, target_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", target_hash],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        subprocess.run(
            ["git", "clean", "-xdf"],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        for step in steps:
            check_command(step, target_dir, target)


# Actual Tests broken up into separate functions so progress is visible
def test_flask() -> None:
    run_repo("flask")


def test_create_react_app() -> None:
    run_repo("create-react-app")


def test_django_example() -> None:
    run_repo("django-example")


def test_instabot() -> None:
    run_repo("instabot")
