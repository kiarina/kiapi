"""Merge an edit request with settings defaults into the complete EditParams."""

import random

from .._settings import QwenSettings
from .._views.edit_params import EditParams
from .._views.edit_request import EditRequest


def resolve_edit_params(
    settings: QwenSettings,
    req: EditRequest,
    *,
    variant: str,
    image_paths: list[str],
) -> EditParams:
    return EditParams(
        model=variant,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        image_file_ids=[],
        image_paths=image_paths,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=req.width if req.width is not None else settings.default_width,
        height=req.height if req.height is not None else settings.default_height,
        steps=req.steps if req.steps is not None else settings.edit_steps,
        guidance=req.guidance if req.guidance is not None else settings.edit_guidance,
        quantize=req.quantize
        if req.quantize is not None
        else settings.default_quantize,
        scheduler=req.scheduler,
        format=req.format,
        quality=req.quality,
        loras=req.loras,
    )
