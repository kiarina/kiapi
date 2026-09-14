"""Family packages — one subpackage per family (dir == family).

Each family exposes a ``register()`` that populates the global model + help
registries (see core/model, core/help). Registration is explicit, not an import
side effect: the CLI bootstrap calls each family's ``register`` before starting
the API server or running setup/check commands.

Shared building blocks reused across families live here too: the common
request-error types and the Files-API path resolver.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.CapabilityError import CapabilityError
    from ._exceptions.ValidationError import ValidationError
    from ._helpers.attach_mflux_progress import attach_mflux_progress
    from ._helpers.get_file_path import get_file_path
    from ._helpers.resolve_file_ref import resolve_file_ref

__all__ = [
    "CapabilityError",
    "ValidationError",
    "attach_mflux_progress",
    "get_file_path",
    "resolve_file_ref",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "CapabilityError": "._exceptions.CapabilityError",
        "ValidationError": "._exceptions.ValidationError",
        "attach_mflux_progress": "._helpers.attach_mflux_progress",
        "get_file_path": "._helpers.get_file_path",
        "resolve_file_ref": "._helpers.resolve_file_ref",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
