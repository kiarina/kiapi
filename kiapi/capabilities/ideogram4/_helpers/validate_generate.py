from kiapi.capabilities import ValidationError

from .._settings import settings_manager
from .._views.generate_request import GenerateRequest

_MULTIPLE = 16


def validate_generate(req: GenerateRequest) -> None:
    settings = settings_manager.get_settings()
    width = req.width if req.width is not None else settings.default_width
    height = req.height if req.height is not None else settings.default_height

    if width < settings.min_width or height < settings.min_height:
        raise ValidationError(
            f"width and height must be >= {settings.min_width}x{settings.min_height}"
        )
    if width % _MULTIPLE or height % _MULTIPLE:
        raise ValidationError(f"width and height must be multiples of {_MULTIPLE}")
    if width > settings.max_width or height > settings.max_height:
        raise ValidationError(
            f"size {width}x{height} exceeds the cap {settings.max_width}x{settings.max_height}"
        )

    if req.quantize is not None and req.quantize not in (3, 4, 5, 6, 8):
        raise ValidationError("quantize must be one of 3, 4, 5, 6, 8")

    if isinstance(req.prompt, str) and not req.prompt.strip():
        raise ValidationError("prompt must not be empty")
    if isinstance(req.prompt, dict) and not req.prompt:
        raise ValidationError("prompt JSON must not be empty")
