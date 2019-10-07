import subprocess

from bento.extra.python_tool import PythonTool


def test_venv_sanitization_string_arg():
    """
    Demonstrates that sanitization prevents shell injection with a
    malicious string argument
    """
    bad_args = ['"cat"; echo "dog"']

    cmd = f'echo {" ".join(bad_args)}'

    # NOTE: This is a deliberate demonstration of a shell injection
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, encoding="utf8")
    res, _ = proc.communicate()

    assert res.rstrip() == "cat\ndog"

    env, args = PythonTool.sanitize_arguments(bad_args)
    cmd = f'echo {" ".join(args)}'
    proc = subprocess.Popen(
        cmd, env=env, shell=True, stdout=subprocess.PIPE, encoding="utf8"
    )
    res, _ = proc.communicate()

    assert res.rstrip() == '"cat"; echo "dog"'


def test_venv_sanitization_array_arg():
    """
    Demonstrates that sanitization prevents shell injection with a
    malicious array argument (e.g. '*')
    """
    bad_args = ["*"]

    cmd = f'ls {" ".join(bad_args)}'

    # NOTE: This is a deliberate demonstration of a shell injection
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf8"
    )
    stdout, stderr = proc.communicate()

    # stdout should contain every directory's contents
    assert stdout

    env, args = PythonTool.sanitize_arguments(bad_args)
    cmd = f'ls {" ".join(args)}'
    proc = subprocess.Popen(
        cmd,
        env=env,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf8",
    )
    stdout, stderr = proc.communicate()

    assert not stdout
    assert stderr.rstrip().endswith("No such file or directory")
