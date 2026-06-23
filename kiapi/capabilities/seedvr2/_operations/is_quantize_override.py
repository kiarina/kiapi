"""Decide whether a request's quantize differs from the default.

A True result means the resident model (quantized at its default) can't serve the
request, so ``handle_upscale`` runs a one-off transient model instead.
"""

from .._settings import SeedVR2Settings
from .._views.upscale_request import UpscaleRequest


def is_quantize_override(settings: SeedVR2Settings, req: UpscaleRequest) -> bool:
    return req.quantize is not None and req.quantize != settings.default_quantize
