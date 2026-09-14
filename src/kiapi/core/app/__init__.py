from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._schemas.app_context import AppContext

__all__ = [
    "AppContext",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "AppContext": "._schemas.app_context",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
