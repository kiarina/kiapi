"""h3 family — MiniMax H3 Ref2VA video generation via mlx-serve.

Endpoint: ``POST /v1/video/h3/generate``. Each job starts an mlx-serve process,
generates, and stops it, so this family is transient (``resident=False``).
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
