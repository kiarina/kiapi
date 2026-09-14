"""Merge an LTX-2 generate request with settings defaults."""

import random

from .._settings import LTX2Settings
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(
    settings: LTX2Settings,
    req: GenerateRequest,
    *,
    variant: str,
) -> GenerateParams:
    return GenerateParams(
        model=variant,
        prompt=req.prompt,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=req.width if req.width is not None else settings.default_width,
        height=req.height if req.height is not None else settings.default_height,
        num_frames=(
            req.num_frames
            if req.num_frames is not None
            else settings.default_num_frames
        ),
        fps=req.fps if req.fps is not None else settings.default_fps,
        image_strength=req.image_strength,
        end_image_strength=req.end_image_strength,
        generate_audio=req.generate_audio,
    )
