import os
from pathlib import Path

from _pytest.tmpdir import tmp_path_factory
from bento.extra.python_taint import PythonTaintTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."


def test_run(tmp_path_factory: tmp_path_factory) -> None:
    base_path = BASE_PATH / "tests/integration/python_taint"
    tool = PythonTaintTool(
        context_for(tmp_path_factory, PythonTaintTool.tool_id(), base_path)
    )
    tool.setup()
    violations = tool.results()
    expectation = [
        Violation(
            tool_id="PythonTaint",
            check_id="5001: Possible shell injection",
            path="source.py",
            line=13,
            column=22,
            message="Possible shell injection [5001]: Data from [UserControlled] source(s) may reach [RemoteCodeExecution] sink(s)",
            severity=2,
            syntactic_context="    image = get_image(image_link)\n",
        )
    ]

    assert violations == expectation
