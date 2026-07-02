"""ideogram4 family — Ideogram 4 FP8 text-to-image via mflux.

Endpoint: ``POST /v1/image/ideogram4/generate``. Ideogram 4 is typography-
focused txt2img. It accepts plain text, but structured JSON captions are the
preferred prompt form and are surfaced in help. A ``quantize`` override runs on
a one-off transient model; otherwise the resident model is used.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiapi.capabilities import ValidationError

    from ._helpers.register import register
    from ._helpers.validate_generate import validate_generate
    from ._operations.handle_generate import handle_generate
    from ._settings import settings_manager
    from ._views.generate_request import GenerateRequest

__all__ = [
    "GenerateRequest",
    "ValidationError",
    "handle_generate",
    "register",
    "settings_manager",
    "validate_generate",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "GenerateRequest": "._views.generate_request",
        "ValidationError": "kiapi.capabilities",
        "handle_generate": "._operations.handle_generate",
        "register": "._helpers.register",
        "settings_manager": "._settings",
        "validate_generate": "._helpers.validate_generate",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
