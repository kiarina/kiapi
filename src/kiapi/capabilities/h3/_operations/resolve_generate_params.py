"""Merge a MiniMax H3 generate request with settings defaults."""

import random

from .._settings import H3Settings
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(
    settings: H3Settings,
    req: GenerateRequest,
    *,
    variant: str,
) -> GenerateParams:
    if req.steps is not None:
        steps = req.steps
    elif req.turbo:
        steps = settings.default_turbo_steps
    else:
        steps = settings.default_steps

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
        steps=steps,
        turbo=req.turbo,
        fast=req.fast,
        use_video_audio=req.use_video_audio,
        enhance_prompt=req.enhance_prompt,
    )
