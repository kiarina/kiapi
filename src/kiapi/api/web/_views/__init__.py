from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fetch_api_request import FetchAPIRequest
    from .fetch_error_response import FetchErrorResponse

__all__ = [
    "FetchAPIRequest",
    "FetchErrorResponse",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "FetchAPIRequest": ".fetch_api_request",
        "FetchErrorResponse": ".fetch_error_response",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
