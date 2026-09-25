from kiapi.capabilities import ValidationError

from .._constants.image_21 import IMAGE_21_VARIANT
from .._settings import QwenSettings
from .._views.edit_request import EditRequest
from .._views.generate_request import GenerateRequest

_MULTIPLE = 16
_IMAGE_21_MULTIPLE = 32


def validate_common(
    req: GenerateRequest | EditRequest,
    settings: QwenSettings,
    *,
    role: str,
    variant: str,
) -> None:
    if variant == IMAGE_21_VARIANT:
        _validate_image_21(req, settings)
        return

    width = req.width if req.width is not None else settings.default_width
    height = req.height if req.height is not None else settings.default_height
    _validate_size(
        width,
        height,
        multiple=_MULTIPLE,
        max_width=settings.max_width,
        max_height=settings.max_height,
    )

    default_steps = settings.edit_steps if role == "edit" else settings.generate_steps
    steps = req.steps if req.steps is not None else default_steps
    if steps < 1 or steps > settings.max_steps:
        raise ValidationError(f"steps must be in 1..{settings.max_steps}")
    _validate_quantize(req)
    if len(req.loras) > settings.max_loras:
        raise ValidationError(f"at most {settings.max_loras} loras may be applied")


def _validate_image_21(
    req: GenerateRequest | EditRequest, settings: QwenSettings
) -> None:
    # An edit that omits the size derives it from the last reference image.
    if (
        isinstance(req, GenerateRequest)
        or req.width is not None
        or req.height is not None
    ):
        width = req.width if req.width is not None else settings.default_width
        height = req.height if req.height is not None else settings.default_height
        _validate_size(
            width,
            height,
            multiple=_IMAGE_21_MULTIPLE,
            max_width=settings.image_21_max_width,
            max_height=settings.image_21_max_height,
        )

    steps = req.steps if req.steps is not None else settings.image_21_steps
    if steps < 2 or steps > settings.max_steps:
        raise ValidationError(f"steps must be in 2..{settings.max_steps} for image-2.1")
    if req.guidance is not None and req.guidance < 1:
        raise ValidationError("guidance must be at least 1 for image-2.1")
    _validate_quantize(req)
    if req.loras:
        raise ValidationError("image-2.1 does not support loras")


def _validate_size(
    width: int, height: int, *, multiple: int, max_width: int, max_height: int
) -> None:
    if width <= 0 or height <= 0:
        raise ValidationError("width and height must be positive")
    if width % multiple or height % multiple:
        raise ValidationError(f"width and height must be multiples of {multiple}")
    if width > max_width or height > max_height:
        raise ValidationError(
            f"size {width}x{height} exceeds the cap {max_width}x{max_height}"
        )


def _validate_quantize(req: GenerateRequest | EditRequest) -> None:
    if req.quantize is not None and req.quantize not in (3, 4, 5, 6, 8):
        raise ValidationError("quantize must be one of 3, 4, 5, 6, 8")
