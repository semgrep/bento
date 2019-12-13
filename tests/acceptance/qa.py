import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

import bento.constants

BENTO_REPO_ROOT = str(Path(__file__).parent.parent.parent.resolve())


def write_expected_file(filename: str, output: str) -> None:
    with open(filename, "w") as file:
        stripped = remove_trailing_space(output)
        file.write(stripped)


def remove_trailing_space(string: str) -> str:
    return "\n".join([o.rstrip() for o in string.split("\n")])


def remove_timing_seconds(string: str) -> str:
    dynamic_seconds = re.compile(r"([\s\S]* \d+ finding.?s.? in )\d+\.\d+( s[\s\S]*)")
    result = re.sub(dynamic_seconds, r"\1\2", string)
    return result


def match_expected(output: str, expected: str) -> bool:
    """Checks that OUTPUT matches EXPECTED

    Checks that OUTPUT and EXPECTED are exact
    matches ignoring trailing whitespace

    """
    output = remove_trailing_space(output)
    expected = remove_trailing_space(expected)

    # Handle dynamic characters (for now just timing info)
    if "finding(s) in" in expected or "findings in" in expected:
        output = remove_timing_seconds(output)
        expected = remove_timing_seconds(expected)

    if output.strip() != expected.strip():
        print("==== EXPECTED ====")
        print(expected)
        print("==== ACTUAL ====")
        print(output)
    return output.strip() == expected.strip()


def check_command(step: Any, pwd: str, target: str, rewrite: bool) -> None:
    """Runs COMMAND in with cwd=PWD and checks that the returncode, stdout, and stderr
    match their respective expected values.

    If rewrite is True, overwrites expected files with output of running step, skipping
    output match verification
    """
    command = step["command"]

    test_identifier = f"Target:{target} Step:{step['name']}"
    env = os.environ.copy()
    env[bento.constants.BENTO_EMAIL_VAR] = bento.constants.QA_TEST_EMAIL_ADDRESS
    env[bento.constants.BENTO_TEST_VAR] = "1"
    substituted = [
        part.replace("__BENTO_REPO_ROOT__", BENTO_REPO_ROOT) for part in command
    ]

    runned = subprocess.run(
        substituted,
        # Note that we can't use BENTO_BASE_PATH since the acceptance tests
        # depend on hook installation, which uses the working directory.
        cwd=pwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    print(f"======= {test_identifier} ========")
    print("Command return code:", runned.returncode)

    if "returncode" in step:
        expected_returncode = step["returncode"]
        if runned.returncode != expected_returncode:
            print(f"Run stdout: {runned.stdout}")
            print(f"Run stderr: {runned.stderr}")
        assert runned.returncode == expected_returncode, test_identifier

    if "expected_out" in step:
        expected_out_file = step.get("expected_out")
        if rewrite and expected_out_file is not None:
            write_expected_file(
                f"tests/acceptance/{target}/{expected_out_file}", runned.stdout
            )
        else:
            if expected_out_file is None:
                expected_out = ""
            else:
                with open(f"tests/acceptance/{target}/{expected_out_file}") as file:
                    expected_out = file.read()

            assert match_expected(
                runned.stdout, expected_out
            ), f"{test_identifier}: stdout"

    if "expected_err" in step:
        expected_err_file = step.get("expected_err")

        if rewrite and expected_err_file is not None:
            write_expected_file(
                f"tests/acceptance/{target}/{expected_err_file}", runned.stderr
            )
        else:
            if expected_err_file is None:
                expected_err = ""
            else:
                with open(f"tests/acceptance/{target}/{expected_err_file}") as file:
                    expected_err = file.read()

            assert match_expected(
                runned.stderr, expected_err
            ), f"{test_identifier}: stderr"


def run_repo(
    target: str, pre: Optional[Callable[[Path], None]] = None, rewrite: bool = False
) -> None:
    """
    Runs commands for a repository definition file.

    :param target: Subdirectory where the repository's commands are stored
    :param pre: A setup function to run after the repository is checked out, but prior to running commands
    """
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

        if pre:
            pre(Path(target_dir))

        for step in steps:
            check_command(step, target_dir, target, rewrite)


# Actual Tests broken up into separate functions so progress is visible
def test_flask() -> None:
    run_repo("flask")


def run_create_react_app(rewrite: bool) -> None:
    # eslint runs forever unless we ignore 'lib/'
    def setup_ignores(root: Path) -> None:
        with (root / ".gitignore").open("a") as gitignore:
            gitignore.writelines(["lib/\n"])

    run_repo("create-react-app", pre=setup_ignores, rewrite=rewrite)


def test_create_react_app() -> None:
    run_create_react_app(rewrite=False)


def test_django_example() -> None:
    run_repo("django-example")


def test_instabot() -> None:
    run_repo("instabot")


if __name__ == "__main__":
    run_repo("flask", rewrite=True)
    run_repo("django-example", rewrite=True)
    run_repo("instabot", rewrite=True)
    run_create_react_app(rewrite=True)
