from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import (
        BaseRelay,
        Relay,
        RelayDelivery,
        RelayError,
        RelayFileBody,
        RelayHealth,
        RelayJsonBody,
        RelayMethod,
        RelayMultipartBody,
        RelayMultipartFile,
        RelayName,
        RelayRequest,
        RelayRequestError,
        RelayResponse,
        RelayRunner,
        RelaySettings,
        RelaySpecifier,
        build_relay_response,
        get_or_create_node_id,
        new_relay_session_id,
        relay_registry,
        settings_manager,
    )

__all__ = [
    "BaseRelay",
    "Relay",
    "RelayDelivery",
    "RelayError",
    "RelayFileBody",
    "RelayHealth",
    "RelayJsonBody",
    "RelayMethod",
    "RelayMultipartBody",
    "RelayMultipartFile",
    "RelayName",
    "RelayRequest",
    "RelayRequestError",
    "RelayResponse",
    "RelayRunner",
    "RelaySettings",
    "RelaySpecifier",
    "build_relay_response",
    "get_or_create_node_id",
    "new_relay_session_id",
    "relay_registry",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "BaseRelay": ".core",
        "Relay": ".core",
        "RelayDelivery": ".core",
        "RelayError": ".core",
        "RelayFileBody": ".core",
        "RelayHealth": ".core",
        "RelayJsonBody": ".core",
        "RelayMethod": ".core",
        "RelayMultipartBody": ".core",
        "RelayMultipartFile": ".core",
        "RelayName": ".core",
        "RelayRequest": ".core",
        "RelayRequestError": ".core",
        "RelayResponse": ".core",
        "RelayRunner": ".core",
        "RelaySettings": ".core",
        "RelaySpecifier": ".core",
        "build_relay_response": ".core",
        "get_or_create_node_id": ".core",
        "new_relay_session_id": ".core",
        "relay_registry": ".core",
        "settings_manager": ".core",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
