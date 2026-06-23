from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    from kiapi.capabilities.acestep import GenerateRequest, handle_generate

    result, artifacts = handle_generate(
        ctx,
        GenerateRequest(
            model=spec.name,
            prompt="short simple electronic tone",
            lyrics="[Instrumental]",
            duration=5,
            inference_steps=1,
            seed=1,
        ),
    )
    return build_check_result(spec, result, artifacts)
