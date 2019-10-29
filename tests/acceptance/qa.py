import shutil
import subprocess
from typing import Any, List, Union

import yaml

Expectation = Union[str, List[str]]


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

    runned = subprocess.run(
        command,
        cwd=pwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    if expected_returncode is not None:
        assert runned.returncode == expected_returncode
    if expected_out is not None:
        match_expected(runned.stdout, expected_out, f"{test_identifier}: stdout")
    if expected_err is not None:
        match_expected(runned.stderr, expected_err, f"{test_identifier}: stderr")


def run_repo(target: str) -> None:
    with open(f"tests/acceptance/{target}/commands.yaml") as file:
        info = yaml.safe_load(file)

    target_repo = info["target_repo"]
    target_hash = info["target_hash"]
    target_dir = "target_dir"
    steps = info["steps"]

    # Clone and checkout repo
    shutil.rmtree(target_dir, ignore_errors=True)
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

    # Cleanup repo
    shutil.rmtree(target_dir)


# Actual Tests broken up into separate functions so progress is visible
def test_flask() -> None:
    run_repo("flask")


def test_create_react_app() -> None:
    run_repo("create-react-app")


def test_django_example() -> None:
    run_repo("django-example")


def test_instabot() -> None:
    run_repo("instabot")
