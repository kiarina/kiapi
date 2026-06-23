from kiapi.capabilities import ValidationError

from .._settings import settings_manager
from .._views.generate_request import GenerateRequest


def validate_generate(req: GenerateRequest, *, variant: str) -> None:
    del variant

    settings = settings_manager.get_settings()
    if req.duration > settings.max_duration:
        raise ValidationError(
            f"duration {req.duration}s exceeds max {settings.max_duration}s"
        )
