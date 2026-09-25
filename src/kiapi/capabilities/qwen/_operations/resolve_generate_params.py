"""Merge a generate request with settings defaults into the complete GenerateParams."""

import random

from .._constants.image_21 import IMAGE_21_VARIANT
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
    is_21 = variant == IMAGE_21_VARIANT
    default_steps = settings.image_21_steps if is_21 else settings.generate_steps
    default_guidance = (
        settings.image_21_guidance if is_21 else settings.generate_guidance
    )
    default_quantize = (
        settings.image_21_quantize if is_21 else settings.default_quantize
    )
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
        steps=req.steps if req.steps is not None else default_steps,
        guidance=req.guidance if req.guidance is not None else default_guidance,
        quantize=req.quantize if req.quantize is not None else default_quantize,
        scheduler=req.scheduler,
        format=req.format,
        quality=req.quality,
        loras=req.loras,
    )
