"""ltx2 family — LTX-2 distilled video generation via mlx-video.

Endpoint: ``POST /v1/video/ltx2/generate`` (multipart; T2V/I2V/A2V inferred from
attached inputs). mlx-video loads and frees its own weights per call, so this
family is transient (``resident=False``): the service reserves budget room before
each run instead of holding a model.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiapi.capabilities import ValidationError

    from ._helpers.register import register
    from ._helpers.validate_generate import validate_generate
    from ._operations.detect_mode import detect_mode
    from ._operations.handle_generate import handle_generate
    from ._settings import settings_manager
    from ._views.generate_request import GenerateRequest

__all__ = [
    "GenerateRequest",
    "ValidationError",
    "detect_mode",
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
        "detect_mode": "._operations.detect_mode",
        "handle_generate": "._operations.handle_generate",
        "register": "._helpers.register",
        "settings_manager": "._settings",
        "validate_generate": "._helpers.validate_generate",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
