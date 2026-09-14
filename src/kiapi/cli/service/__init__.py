from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._services import service_manager

__all__ = [
    "service_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    # ``service_manager`` is a submodule, so return the module itself.
    module_map = {
        "service_manager": "._services.service_manager",
    }

    globals()[name] = import_module(module_map[name], __name__)
    return globals()[name]
