from pathlib import Path
from typing import Dict, Any, Union

class MonkeyPatch:
    def setattr(self, obj: Any, name: str, value: Any, raising: bool = True) -> None: ...
    def delattr(self, obj: Any, name: str, raising: bool = True) -> None: ...
    def setitem(self, mapping: Dict, name: str, value: Any) -> None: ...
    def delitem(self, obj: Any, name: str, raising: bool = True) -> None: ...
    def setenv(self, name: str, value: Any, prepend: bool = False) -> None: ...
    def delenv(self, name: str, raising: bool = True) -> None: ...
    def syspath_prepend(self, path: str) -> None: ...
    def chdir(self, path: Union[str, Path]) -> None: ...
