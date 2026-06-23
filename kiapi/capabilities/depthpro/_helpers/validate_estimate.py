from PIL import Image

from kiapi.capabilities import ValidationError

from .._settings import settings_manager
from .._views.estimate_request import EstimateRequest


def validate_estimate(
    req: EstimateRequest,
    *,
    image_path: str | None = None,
) -> None:
    settings = settings_manager.get_settings()

    if req.quantize is not None and req.quantize not in (3, 4, 5, 6, 8):
        raise ValidationError("quantize must be one of 3, 4, 5, 6, 8")

    if image_path is None:
        return

    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception as exc:
        raise ValidationError(f"input image could not be opened: {exc}")  # noqa: B904

    pixels = width * height
    if pixels > settings.max_input_pixels:
        raise ValidationError(
            f"input image has {pixels} pixels, exceeding the cap {settings.max_input_pixels}"
        )
