"""qwen family — Qwen Image generation/editing via mflux.

Endpoints: ``POST /v1/image/qwen/{generate,edit}``. ``generate`` is txt2img by
default and img2img when ``init_image_file_id`` is supplied; ``edit`` does
natural-language single/multi-image editing. LoRA adapters and a ``quantize``
override run on a one-off transient model; otherwise the resident model is used.
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_edit import validate_edit
from ._helpers.validate_generate import validate_generate
from ._operations.handle_edit import handle_edit
from ._operations.handle_generate import handle_generate
from ._settings import settings_manager
from ._views.edit_request import EditRequest
from ._views.generate_request import GenerateRequest

__all__ = [
    "EditRequest",  # ._views
    "GenerateRequest",  # ._views
    "ValidationError",  # kiapi.capabilities
    "handle_edit",  # ._operations
    "handle_generate",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
    "validate_edit",  # ._helpers
    "validate_generate",  # ._helpers
]
