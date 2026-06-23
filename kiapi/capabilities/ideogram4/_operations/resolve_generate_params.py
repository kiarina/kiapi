"""Merge a generate request with settings defaults into the complete GenerateParams."""

import random

from .._settings import Ideogram4Settings
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(
    settings: Ideogram4Settings,
    req: GenerateRequest,
    *,
    variant: str,
) -> GenerateParams:
    return GenerateParams(
        model=variant,
        prompt=req.prompt,
        preset=req.preset,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=req.width if req.width is not None else settings.default_width,
        height=req.height if req.height is not None else settings.default_height,
        quantize=req.quantize
        if req.quantize is not None
        else settings.default_quantize,
        strict_caption_validation=req.strict_caption_validation,
        warn_on_caption_issues=req.warn_on_caption_issues,
        format=req.format,
        quality=req.quality,
    )
