from kiapi.capabilities import ValidationError

from .._settings import settings_manager
from .._views.speech_request import SpeechRequest
from .resolve_language import resolve_language


def validate_speech(req: SpeechRequest) -> None:
    settings = settings_manager.get_settings()
    if len(req.input) > settings.max_input_chars:
        raise ValidationError(
            f"input is {len(req.input)} characters; the maximum is {settings.max_input_chars}"
        )
    if req.speed != 1.0:
        raise ValidationError("speed is not supported; only 1.0")
    if req.instructions:
        raise ValidationError("instructions are not supported by voice cloning")
    resolve_language(req.language)
