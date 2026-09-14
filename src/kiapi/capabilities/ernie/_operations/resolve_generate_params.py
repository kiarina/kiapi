"""Merge a generate request with settings defaults into the complete GenerateParams."""

import random

from .._settings import ErnieSettings
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(
    settings: ErnieSettings,
    req: GenerateRequest,
    *,
    variant: str,
) -> GenerateParams:
    return GenerateParams(
        model=variant,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=req.width if req.width is not None else settings.default_width,
        height=req.height if req.height is not None else settings.default_height,
        steps=req.steps
        if req.steps is not None
        else settings.default_steps.get(variant, 8),
        guidance=(
            req.guidance
            if req.guidance is not None
            else settings.default_guidance.get(variant, 1.0)
        ),
        quantize=(
            req.quantize
            if req.quantize is not None
            else settings.default_quantize.get(variant)
        ),
        scheduler=req.scheduler,
        format=req.format,
        quality=req.quality,
        loras=req.loras,
    )
