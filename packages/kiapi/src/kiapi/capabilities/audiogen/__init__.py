"""audiogen family — text→sound-effect via AudioGen (mlx-audiocraft).

Integrates mlx-audiocraft-server. Endpoint: ``POST /v1/audio/audiogen/generate``;
sync/async via `mode`, artifacts in the Files API. ``weight_gb`` measured on
device (model card ~3.6 GB). The variant ``medium`` is the only AudioGen size;
the family name (audiogen) is the AudioGen model family, distinct from the
mlx-audiocraft library (which also hosts MusicGen).
"""

from kiapi.capabilities import ValidationError

from ._helpers.register import register
from ._helpers.validate_generate import validate_generate
from ._operations.handle_generate import handle_generate
from ._settings import settings_manager
from ._views.generate_request import GenerateRequest

__all__ = [
    "GenerateRequest",
    "ValidationError",
    "handle_generate",
    "register",
    "settings_manager",
    "validate_generate",
]
