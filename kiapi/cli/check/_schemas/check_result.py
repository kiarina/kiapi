from dataclasses import dataclass, field
from typing import Any

from kiapi.core.file import FileID


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str
    artifacts: list[FileID] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
