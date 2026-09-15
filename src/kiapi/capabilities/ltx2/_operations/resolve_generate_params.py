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
    if req.auto_duration:
        num_frames = None
    elif req.num_frames is not None:
        num_frames = req.num_frames
    else:
        num_frames = settings.default_num_frames

    return GenerateParams(
        model=variant,
        prompt=req.prompt,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        width=req.width if req.width is not None else settings.default_width,
        height=req.height if req.height is not None else settings.default_height,
        num_frames=num_frames,
        fps=req.fps if req.fps is not None else settings.default_fps,
        image_strength=req.image_strength,
        end_image_strength=req.end_image_strength,
        generate_audio=req.generate_audio,
        enhance_prompt=req.enhance_prompt,
        pipeline=req.pipeline,
        video_decoder=req.video_decoder,
    )
