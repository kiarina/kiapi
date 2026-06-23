"""Merge an edit request with settings defaults into the complete EditParams."""

import random

from .._settings import ErnieSettings
from .._views.edit_params import EditParams
from .._views.edit_request import EditRequest


def resolve_edit_params(
    settings: ErnieSettings,
    req: EditRequest,
    *,
    variant: str,
    image_path: str,
) -> EditParams:
    return EditParams(
        model=variant,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        image_file_id="",
        image_path=image_path,
        image_strength=req.image_strength,
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
