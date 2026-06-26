"""Merge an upscale request with settings defaults into the complete UpscaleParams."""

import random

from .._settings import SeedVR2Settings
from .._views.upscale_params import UpscaleParams
from .._views.upscale_request import UpscaleRequest


def resolve_upscale_params(
    settings: SeedVR2Settings,
    req: UpscaleRequest,
    *,
    variant: str,
    image_file_id: str,
    image_path: str,
) -> UpscaleParams:
    return UpscaleParams(
        model=variant,
        image_file_id=image_file_id,
        image_path=image_path,
        resolution=req.resolution,
        softness=req.softness,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        quantize=req.quantize
        if req.quantize is not None
        else settings.default_quantize,
        format=req.format,
        quality=req.quality,
    )
