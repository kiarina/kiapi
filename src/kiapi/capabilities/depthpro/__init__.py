"""depthpro family — Depth Pro image → depth map estimation via mflux.

Endpoint: ``POST /v1/image/depthpro/estimate``. Depth Pro consumes one input
image from the Files API and stores a displayable grayscale depth PNG, plus an
optional compressed NPZ with the raw depth array.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiapi.capabilities import ValidationError

    from ._helpers.register import register
    from ._helpers.validate_estimate import validate_estimate
    from ._operations.handle_estimate import handle_estimate
    from ._settings import settings_manager
    from ._views.estimate_request import EstimateRequest

__all__ = [
    "EstimateRequest",
    "ValidationError",
    "handle_estimate",
    "register",
    "settings_manager",
    "validate_estimate",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "EstimateRequest": "._views.estimate_request",
        "ValidationError": "kiapi.capabilities",
        "handle_estimate": "._operations.handle_estimate",
        "register": "._helpers.register",
        "settings_manager": "._settings",
        "validate_estimate": "._helpers.validate_estimate",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
