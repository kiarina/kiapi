"""qwen family — Qwen Image generation/editing via mflux.

Endpoints: ``POST /v1/image/qwen/{generate,edit}``. ``generate`` is txt2img by
default and img2img when ``init_image_file_id`` is supplied; ``edit`` does
natural-language single/multi-image editing. LoRA adapters and a ``quantize``
override run on a one-off transient model; otherwise the resident model is used.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    "EditRequest",
    "GenerateRequest",
    "ValidationError",
    "handle_edit",
    "handle_generate",
    "register",
    "settings_manager",
    "validate_edit",
    "validate_generate",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "EditRequest": "._views.edit_request",
        "GenerateRequest": "._views.generate_request",
        "ValidationError": "kiapi.capabilities",
        "handle_edit": "._operations.handle_edit",
        "handle_generate": "._operations.handle_generate",
        "register": "._helpers.register",
        "settings_manager": "._settings",
        "validate_edit": "._helpers.validate_edit",
        "validate_generate": "._helpers.validate_generate",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
