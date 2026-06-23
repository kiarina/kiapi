from kiapi.capabilities.web import FetchRequest, handle_fetch
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    result, artifacts = handle_fetch(
        ctx,
        FetchRequest(url="https://example.com"),
    )
    return build_check_result(spec, result, artifacts)
