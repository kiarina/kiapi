from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._schemas.capability_spec import CapabilitySpec
    from ._services.capability_spec_registry import (
        CapabilitySpecRegistry,
        capability_spec_registry,
    )

__all__ = [
    "CapabilitySpec",
    "CapabilitySpecRegistry",
    "capability_spec_registry",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "CapabilitySpec": "._schemas.capability_spec",
        "CapabilitySpecRegistry": "._services.capability_spec_registry",
        "capability_spec_registry": "._services.capability_spec_registry",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
