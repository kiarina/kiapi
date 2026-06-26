from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.create_local_relay import create_local_relay
    from ._schemas.local_relay_notification import LocalRelayNotification
    from ._services.local_relay import LocalRelay
    from ._services.local_relay_delivery import LocalRelayDelivery
    from ._settings import LocalRelaySettings, settings_manager

__all__ = [
    "LocalRelay",
    "LocalRelayDelivery",
    "LocalRelayNotification",
    "LocalRelaySettings",
    "create_local_relay",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "LocalRelay": "._services.local_relay",
        "LocalRelayDelivery": "._services.local_relay_delivery",
        "LocalRelayNotification": "._schemas.local_relay_notification",
        "LocalRelaySettings": "._settings",
        "create_local_relay": "._helpers.create_local_relay",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
