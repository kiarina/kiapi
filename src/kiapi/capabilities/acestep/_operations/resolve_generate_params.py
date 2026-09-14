"""Merge an ACE-Step generate request into the model-layer contract."""

from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest


def resolve_generate_params(req: GenerateRequest, *, variant: str) -> GenerateParams:
    return GenerateParams(
        model=variant,
        prompt=req.prompt,
        lyrics=req.lyrics,
        duration=req.duration,
        lang=req.lang,
        seed=req.seed,
        inference_steps=req.inference_steps,
        guidance_scale=req.guidance_scale,
        shift=req.shift,
    )
