"""Merge an ACE-Step repaint request into the model-layer contract."""

from .._views.repaint_params import RepaintParams
from .._views.repaint_request import RepaintRequest


def resolve_repaint_params(
    req: RepaintRequest, *, variant: str, source_file_id: str, src_audio: str
) -> RepaintParams:
    return RepaintParams(
        model=variant,
        src=source_file_id,
        src_audio=src_audio,
        prompt=req.prompt,
        start=req.start,
        end=req.end,
        strength=req.strength,
        seed=req.seed,
        inference_steps=req.inference_steps,
        guidance_scale=req.guidance_scale,
        shift=req.shift,
    )
