from kiapi.capabilities.ltx2 import GenerateRequest, handle_generate
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    result, artifacts = handle_generate(
        ctx,
        GenerateRequest(
            model=spec.name,
            prompt="a small blue cube rotating slowly",
            width=256,
            height=256,
            num_frames=9,
            fps=8,
            seed=1,
            image_strength=1.0,
            end_image_strength=None,
            generate_audio=False,
        ),
        mode="T2V",
    )
    return build_check_result(spec, result, artifacts)
