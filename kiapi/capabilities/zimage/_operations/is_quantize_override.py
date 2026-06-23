"""Decide whether a request's quantize differs from the variant default."""

from .._settings import ZimageSettings
from .._views.generate_request import GenerateRequest


def is_quantize_override(
    settings: ZimageSettings, req: GenerateRequest, *, variant: str
) -> bool:
    default_quantize = settings.default_quantize.get(variant)
    return req.quantize is not None and req.quantize != default_quantize
