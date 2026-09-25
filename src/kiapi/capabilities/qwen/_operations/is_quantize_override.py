"""Decide whether a request's quantize differs from the variant default.

A True result means the resident model (quantized at its default) can't serve the
request, so ``handle_*`` runs a one-off transient model instead.
"""

from .._constants.image_21 import IMAGE_21_VARIANT
from .._settings import QwenSettings
from .._views.edit_request import EditRequest
from .._views.generate_request import GenerateRequest


def is_quantize_override(
    settings: QwenSettings, req: GenerateRequest | EditRequest, *, variant: str
) -> bool:
    default = (
        settings.image_21_quantize
        if variant == IMAGE_21_VARIANT
        else settings.default_quantize
    )
    return req.quantize is not None and req.quantize != default
