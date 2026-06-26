from kiapi.capabilities.web import SearchRequest, handle_search
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    result, artifacts = handle_search(
        ctx,
        SearchRequest(query="kiapi", max_results=1),
    )
    return build_check_result(spec, result, artifacts)
