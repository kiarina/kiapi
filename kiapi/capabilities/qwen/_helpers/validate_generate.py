from kiapi.capabilities import ValidationError

from .._operations.validate_common import validate_common
from .._settings import settings_manager
from .._views.generate_request import GenerateRequest


def validate_generate(req: GenerateRequest) -> None:
    settings = settings_manager.get_settings()
    validate_common(req, settings, role="generate")
    if req.image_strength is not None and not 0 <= req.image_strength <= 1:
        raise ValidationError("image_strength must be in 0..1")
