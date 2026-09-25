"""Merge an edit request with settings defaults into the complete EditParams."""

import math
import random

from .._constants.image_21 import IMAGE_21_VARIANT
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
    is_21 = variant == IMAGE_21_VARIANT
    width, height = _resolve_size(settings, req, is_21=is_21, image_paths=image_paths)
    default_steps = settings.image_21_steps if is_21 else settings.edit_steps
    default_guidance = settings.image_21_guidance if is_21 else settings.edit_guidance
    default_quantize = (
        settings.image_21_quantize if is_21 else settings.default_quantize
    )
    return EditParams(
        model=variant,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        image_file_ids=[],
        image_paths=image_paths,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=width,
        height=height,
        steps=req.steps if req.steps is not None else default_steps,
        guidance=req.guidance if req.guidance is not None else default_guidance,
        quantize=req.quantize if req.quantize is not None else default_quantize,
        scheduler=req.scheduler,
        format=req.format,
        quality=req.quality,
        loras=req.loras,
        reference_resolution=settings.image_21_reference_resolution if is_21 else None,
    )


def _resolve_size(
    settings: QwenSettings,
    req: EditRequest,
    *,
    is_21: bool,
    image_paths: list[str],
) -> tuple[int, int]:
    if not is_21 or (req.width is not None and req.height is not None):
        return (
            req.width if req.width is not None else settings.default_width,
            req.height if req.height is not None else settings.default_height,
        )

    # Same rule as mflux: the last reference's aspect ratio at the reference budget.
    from PIL import Image, ImageOps

    with Image.open(image_paths[-1]) as image:
        w, h = ImageOps.exif_transpose(image).size
    ratio = w / h
    side = settings.image_21_reference_resolution
    auto_w = math.sqrt(side * side * ratio)
    auto_h = auto_w / ratio
    return (
        req.width if req.width is not None else max(32, round(auto_w / 32) * 32),
        req.height if req.height is not None else max(32, round(auto_h / 32) * 32),
    )
