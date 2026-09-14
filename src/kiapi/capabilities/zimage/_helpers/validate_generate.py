from kiapi.capabilities import ValidationError

from .._settings import ZimageSettings, settings_manager
from .._views.generate_request import GenerateRequest

_MULTIPLE = 16


def validate_generate(req: GenerateRequest, *, variant: str) -> None:
    settings = settings_manager.get_settings()
    _validate_generate(req, settings, variant=variant)


def _validate_generate(
    req: GenerateRequest, settings: ZimageSettings, *, variant: str
) -> None:
    width = req.width if req.width is not None else settings.default_width
    height = req.height if req.height is not None else settings.default_height

    if width <= 0 or height <= 0:
        raise ValidationError("width and height must be positive")
    if width % _MULTIPLE or height % _MULTIPLE:
        raise ValidationError(f"width and height must be multiples of {_MULTIPLE}")
    if width > settings.max_width or height > settings.max_height:
        raise ValidationError(
            f"size {width}x{height} exceeds the cap {settings.max_width}x{settings.max_height}"
        )

    steps = (
        req.steps if req.steps is not None else settings.default_steps.get(variant, 9)
    )
    if steps < 1 or steps > settings.max_steps:
        raise ValidationError(f"steps must be in 1..{settings.max_steps}")
    if req.quantize is not None and req.quantize not in (3, 4, 5, 6, 8):
        raise ValidationError("quantize must be one of 3, 4, 5, 6, 8")
    if len(req.loras) > settings.max_loras:
        raise ValidationError(f"at most {settings.max_loras} loras may be applied")
