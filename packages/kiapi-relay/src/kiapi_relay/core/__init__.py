from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.relay_request_error import RelayRequestError
    from ._helpers.build_relay_response import build_relay_response
    from ._helpers.get_or_create_node_id import get_or_create_node_id
    from ._helpers.new_relay_session_id import new_relay_session_id
    from ._instances.relay_registry import relay_registry
    from ._schemas.relay_file_body import RelayFileBody
    from ._schemas.relay_json_body import RelayJsonBody
    from ._schemas.relay_multipart_body import RelayMultipartBody
    from ._schemas.relay_multipart_file import RelayMultipartFile
    from ._services.base_relay import BaseRelay
    from ._services.relay_runner import RelayRunner
    from ._settings import RelaySettings, settings_manager
    from ._types.relay import Relay
    from ._types.relay_delivery import RelayDelivery
    from ._types.relay_method import RelayMethod
    from ._types.relay_name import RelayName
    from ._types.relay_specifier import RelaySpecifier
    from ._views.relay_error import RelayError
    from ._views.relay_health import RelayHealth
    from ._views.relay_request import RelayRequest
    from ._views.relay_response import RelayResponse

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
        "BaseRelay": "._services.base_relay",
        "Relay": "._types.relay",
        "RelayDelivery": "._types.relay_delivery",
        "RelayError": "._views.relay_error",
        "RelayFileBody": "._schemas.relay_file_body",
        "RelayHealth": "._views.relay_health",
        "RelayJsonBody": "._schemas.relay_json_body",
        "RelayMethod": "._types.relay_method",
        "RelayMultipartBody": "._schemas.relay_multipart_body",
        "RelayMultipartFile": "._schemas.relay_multipart_file",
        "RelayName": "._types.relay_name",
        "RelayRequest": "._views.relay_request",
        "RelayRequestError": "._exceptions.relay_request_error",
        "RelayResponse": "._views.relay_response",
        "RelayRunner": "._services.relay_runner",
        "RelaySettings": "._settings",
        "RelaySpecifier": "._types.relay_specifier",
        "build_relay_response": "._helpers.build_relay_response",
        "get_or_create_node_id": "._helpers.get_or_create_node_id",
        "new_relay_session_id": "._helpers.new_relay_session_id",
        "relay_registry": "._instances.relay_registry",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
