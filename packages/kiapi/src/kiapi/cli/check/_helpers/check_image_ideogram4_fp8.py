from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    from kiapi.capabilities.ideogram4 import GenerateRequest, handle_generate

    result, artifacts = handle_generate(
        ctx,
        GenerateRequest(
            model=spec.name,
            prompt="simple word OK on a plain white card",
            preset="V4_TURBO_12",
            width=256,
            height=256,
            seed=1,
            quality=90,
        ),
    )
    return build_check_result(spec, result, artifacts)
