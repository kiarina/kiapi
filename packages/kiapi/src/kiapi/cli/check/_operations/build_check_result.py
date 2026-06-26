from typing import Any

from kiapi.core.file import FileID
from kiapi.core.model import ModelSpec

from .._schemas.check_result import CheckResult


def build_check_result(
    spec: ModelSpec,
    result: dict[str, Any],
    artifacts: list[FileID],
) -> CheckResult:
    artifact_label = f", artifacts={len(artifacts)}" if artifacts else ""
    return CheckResult(
        ok=True,
        message=f"{spec.domain}/{spec.family}/{spec.name} ok{artifact_label}",
        artifacts=artifacts,
        result=result,
    )
