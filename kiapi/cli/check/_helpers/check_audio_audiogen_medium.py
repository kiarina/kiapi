from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    from kiapi.capabilities.audiogen import GenerateRequest, handle_generate

    result, artifacts = handle_generate(
        ctx,
        GenerateRequest(
            model=spec.name,
            prompt="single soft beep",
            duration=1.0,
            seed=1,
            top_k=1,
            top_p=0.0,
            temperature=1.0,
            cfg_coef=3.0,
        ),
    )
    return build_check_result(spec, result, artifacts)
