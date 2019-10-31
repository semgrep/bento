from typing import Any, Dict, List, Set, TextIO, Union

import attr
import yaml

from bento.violation import Violation

VIOLATIONS_KEY = "violations"

Hash = str
Baseline = Dict[str, Set[Hash]]


def filtered(
    tool_id: str, output: List[Violation], baseline: Baseline
) -> List[Violation]:
    rejects: Set[Hash] = set(baseline.get(tool_id, {}))
    return [
        attr.evolve(v, filtered=v.syntactic_identifier_str() in rejects) for v in output
    ]


def tool_results_to_yml(tool_id: str, results: List[Violation]) -> str:
    with_hashes: Dict[str, Dict[str, Any]] = {
        v.syntactic_identifier_str(): v.to_dict() for v in results
    }
    results_dict = {tool_id: {VIOLATIONS_KEY: with_hashes}}
    return yaml.safe_dump(results_dict, default_flow_style=False)


def yml_to_violation_hashes(yml: Union[str, TextIO]) -> Baseline:
    parsed = yaml.safe_load(yml)
    if parsed is None:
        return {}
    out = {}
    for (tool_id, r) in parsed.items():
        violations = r[VIOLATIONS_KEY]
        hashes = set(violations.keys()) if violations else set()
        out[tool_id] = hashes
    return out
