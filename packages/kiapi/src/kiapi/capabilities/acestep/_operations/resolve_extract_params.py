"""Merge an ACE-Step extract request into one stem's model-layer contract."""

from .._views.extract_params import ExtractParams
from .._views.extract_request import ExtractRequest


def resolve_extract_params(
    req: ExtractRequest,
    *,
    variant: str,
    source_file_id: str,
    src_audio: str,
    target: str,
) -> ExtractParams:
    return ExtractParams(
        model=variant,
        src=source_file_id,
        src_audio=src_audio,
        target=target,
        seed=req.seed,
        inference_steps=req.inference_steps,
        guidance_scale=req.guidance_scale,
        shift=req.shift,
    )
