import json
from typing import Collection

from bento.formatter.base import FindingsMap, Formatter


class Json(Formatter):
    """Formats output as a single JSON blob."""

    def dump(self, findings: FindingsMap) -> Collection[str]:
        json_obj = [
            {
                "tool_id": violation.tool_id,
                "check_id": violation.check_id,
                "line": violation.line,
                "column": violation.column,
                "message": violation.message,
                "severity": violation.severity,
                "path": violation.path,
            }
            for violations in findings.values()
            for violation in violations
        ]
        return [json.dumps(json_obj)]
