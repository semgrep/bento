import os
from pathlib import Path

from bento.extra.python_taint import PythonTaintTool
from bento.violation import Violation
from tests.test_tool import context_for

THIS_PATH = Path(os.path.dirname(__file__))
BASE_PATH = THIS_PATH / ".." / ".." / ".."
TAINT_INTEGRATION_PATH = BASE_PATH / "tests/integration/python_taint"
TAINT_TARGETS = [TAINT_INTEGRATION_PATH / "source.py"]


def test_run(tmp_path: Path) -> None:
    tool = PythonTaintTool(
        context_for(tmp_path, PythonTaintTool.tool_id(), TAINT_INTEGRATION_PATH)
    )
    tool.setup()
    violations = tool.results(TAINT_TARGETS)

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
