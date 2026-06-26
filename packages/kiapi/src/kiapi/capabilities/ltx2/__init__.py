"""ltx2 family — LTX-2 distilled video generation via mlx-video.

Endpoint: ``POST /v1/video/ltx2/generate`` (multipart; T2V/I2V/A2V inferred from
attached inputs). mlx-video loads and frees its own weights per call, so this
family is transient (``resident=False``): the service reserves budget room before
each run instead of holding a model.
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_generate import validate_generate
from ._operations.detect_mode import detect_mode
from ._operations.handle_generate import handle_generate
from ._settings import settings_manager
from ._views.generate_request import GenerateRequest

__all__ = [
    "GenerateRequest",  # ._views
    "ValidationError",  # kiapi.capabilities
    "detect_mode",  # ._operations
    "handle_generate",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
    "validate_generate",  # ._helpers
]
