from kiapi.capabilities.embedding import EmbedRequest, handle_embed
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    result, artifacts = handle_embed(
        ctx,
        EmbedRequest(model=spec.name, text="kiapi check"),
    )
    return build_check_result(spec, result, artifacts)
