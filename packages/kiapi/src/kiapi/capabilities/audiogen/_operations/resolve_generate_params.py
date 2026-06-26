"""Merge an AudioGen request with settings defaults into GenerateParams."""

import random

from .._settings import AudiogenSettings
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(
    settings: AudiogenSettings,
    req: GenerateRequest,
    *,
    variant: str,
) -> GenerateParams:
    return GenerateParams(
        model=variant,
        prompt=req.prompt,
        duration=req.duration,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
        top_k=req.top_k,
        top_p=req.top_p,
        temperature=req.temperature,
        cfg_coef=req.cfg_coef,
    )
