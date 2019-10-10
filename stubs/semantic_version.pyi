from typing import Any, Iterable, Optional

class Version:
    major: int
    minor: int
    patch: int
    def __init__(self: Version, version_string: str, partial: bool = False): ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def __lt__(self, other: "Version") -> bool: ...
    def __le__(self, other: "Version") -> bool: ...
    def __gt__(self, other: "Version") -> bool: ...
    def __ge__(self, other: "Version") -> bool: ...
    def __hash__(self) -> int: ...
    def __cmp__(self, other: Any) -> bool: ...
    def __str__(self) -> str: ...
    def __repr__(self) -> str: ...
    def next_major(self) -> Version: ...

class Spec:
    def __init__(self, *specs_strings: str): ...
    def select(self, versions: Iterable[Version]) -> Optional[Version]: ...

def validate(version: str) -> bool: ...

class NpmSpec:
    def __init__(self, *specs_strings: str): ...
    def match(self, version: Version) -> bool: ...
