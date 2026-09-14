"""Merge an ACE-Step cover request into the model-layer contract."""

from .._views.cover_params import CoverParams
from .._views.cover_request import CoverRequest


def resolve_cover_params(
    req: CoverRequest, *, variant: str, source_file_id: str, src_audio: str
) -> CoverParams:
    return CoverParams(
        model=variant,
        src=source_file_id,
        src_audio=src_audio,
        prompt=req.prompt,
        strength=req.strength,
        duration=req.duration,
        seed=req.seed,
        inference_steps=req.inference_steps,
        guidance_scale=req.guidance_scale,
        shift=req.shift,
    )
