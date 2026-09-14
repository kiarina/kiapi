"""Decide whether a request's quantize differs from the variant default.

A True result means the resident model (quantized at its default) can't serve the
request, so ``handle_generate`` runs a one-off transient model instead.
"""

from .._settings import Ideogram4Settings
from .._views.generate_request import GenerateRequest


def is_quantize_override(settings: Ideogram4Settings, req: GenerateRequest) -> bool:
    return req.quantize is not None and req.quantize != settings.default_quantize
