"""seedvr2 family — diffusion super-resolution / upscale via mflux.

Endpoint: ``POST /v1/image/seedvr2/upscale``. SeedVR2 is not a prompt-driven
image generator; it takes an input image from the Files API and produces an
upscaled image. Variants are ``3b`` (default) and ``7b``. A ``quantize`` override
runs a one-off transient model; otherwise the resident model is used.
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_upscale import validate_upscale
from ._operations.handle_upscale import handle_upscale
from ._settings import settings_manager
from ._views.upscale_request import UpscaleRequest

__all__ = [
    "UpscaleRequest",  # ._views
    "ValidationError",  # kiapi.capabilities
    "handle_upscale",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
    "validate_upscale",  # ._helpers
]
