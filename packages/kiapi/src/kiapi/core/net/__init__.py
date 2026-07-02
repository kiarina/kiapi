"""Networking guards shared across capabilities.

Currently a single SSRF guard for user-supplied URLs; see
:func:`verify_public_url`.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.unsafe_url_error import UnsafeURLError
    from ._helpers.verify_public_url import verify_public_url
    from ._settings import NetSettings, settings_manager

__all__ = [
    "NetSettings",
    "UnsafeURLError",
    "settings_manager",
    "verify_public_url",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "NetSettings": "._settings",
        "UnsafeURLError": "._exceptions.unsafe_url_error",
        "settings_manager": "._settings",
        "verify_public_url": "._helpers.verify_public_url",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
