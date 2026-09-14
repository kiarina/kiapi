"""Decide whether a request's quantize differs from the default.

A True result means the resident model (quantized at its default) can't serve the
request, so ``handle_estimate`` runs a one-off transient model instead.
"""

from .._settings import DepthProSettings
from .._views.estimate_request import EstimateRequest


def is_quantize_override(settings: DepthProSettings, req: EstimateRequest) -> bool:
    return req.quantize is not None and req.quantize != settings.default_quantize
