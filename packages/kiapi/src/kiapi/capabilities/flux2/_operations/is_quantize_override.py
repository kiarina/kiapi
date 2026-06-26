"""Decide whether a request's quantize differs from the variant default.

A True result means the resident model (quantized at its default) can't serve the
request, so ``handle_*`` runs a one-off transient model instead.
"""

from .._settings import Flux2Settings
from .._views.edit_request import EditRequest
from .._views.generate_request import GenerateRequest


def is_quantize_override(
    settings: Flux2Settings, req: GenerateRequest | EditRequest, *, variant: str
) -> bool:
    default_quantize = settings.default_quantize.get(variant)
    return req.quantize is not None and req.quantize != default_quantize
