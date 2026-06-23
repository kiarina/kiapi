"""ideogram4 family — Ideogram 4 FP8 text-to-image via mflux.

Endpoint: ``POST /v1/image/ideogram4/generate``. Ideogram 4 is typography-
focused txt2img. It accepts plain text, but structured JSON captions are the
preferred prompt form and are surfaced in help. A ``quantize`` override runs on
a one-off transient model; otherwise the resident model is used.
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_generate import validate_generate
from ._operations.handle_generate import handle_generate
from ._settings import settings_manager
from ._views.generate_request import GenerateRequest

__all__ = [
    "GenerateRequest",  # ._views
    "ValidationError",  # kiapi.capabilities
    "handle_generate",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
    "validate_generate",  # ._helpers
]
