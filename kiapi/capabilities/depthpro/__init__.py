"""depthpro family — Depth Pro image → depth map estimation via mflux.

Endpoint: ``POST /v1/image/depthpro/estimate``. Depth Pro consumes one input
image from the Files API and stores a displayable grayscale depth PNG, plus an
optional compressed NPZ with the raw depth array.
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_estimate import validate_estimate
from ._operations.handle_estimate import handle_estimate
from ._settings import settings_manager
from ._views.estimate_request import EstimateRequest

__all__ = [
    "EstimateRequest",  # ._views
    "ValidationError",  # kiapi.capabilities
    "handle_estimate",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
    "validate_estimate",  # ._helpers
]
