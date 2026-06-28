from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.create_gcp_relay import create_gcp_relay
    from ._services.gcp_relay import GCPRelay
    from ._services.gcp_relay_delivery import GCPRelayDelivery
    from ._settings import GCPRelaySettings, settings_manager

__all__ = [
    "GCPRelay",
    "GCPRelayDelivery",
    "GCPRelaySettings",
    "create_gcp_relay",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "GCPRelay": "._services.gcp_relay",
        "GCPRelayDelivery": "._services.gcp_relay_delivery",
        "GCPRelaySettings": "._settings",
        "create_gcp_relay": "._helpers.create_gcp_relay",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
