"""Merge a generate request with settings defaults into the complete GenerateParams."""

import random

from .._settings import QwenSettings
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(
    settings: QwenSettings,
    req: GenerateRequest,
    *,
    variant: str,
    init_image_path: str | None,
) -> GenerateParams:
    return GenerateParams(
        kind="img2img" if init_image_path is not None else "txt2img",
        model=variant,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        init_image_file_id=None,
        image_path=init_image_path,
        image_strength=req.image_strength,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=req.width if req.width is not None else settings.default_width,
        height=req.height if req.height is not None else settings.default_height,
        steps=req.steps if req.steps is not None else settings.generate_steps,
        guidance=req.guidance
        if req.guidance is not None
        else settings.generate_guidance,
        quantize=req.quantize
        if req.quantize is not None
        else settings.default_quantize,
        scheduler=req.scheduler,
        format=req.format,
        quality=req.quality,
        loras=req.loras,
    )
