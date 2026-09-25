from kiapi.capabilities import ValidationError

from .._constants.image_21 import IMAGE_21_VARIANT
from .._operations.validate_common import validate_common
from .._settings import settings_manager
from .._views.generate_request import GenerateRequest


def validate_generate(req: GenerateRequest, *, variant: str) -> None:
    settings = settings_manager.get_settings()
    validate_common(req, settings, role="generate", variant=variant)
    if variant == IMAGE_21_VARIANT and req.init_image is not None:
        raise ValidationError(
            "image-2.1 does not take init_image; pass it in `images` on /edit instead"
        )
    if req.image_strength is not None and not 0 <= req.image_strength <= 1:
        raise ValidationError("image_strength must be in 0..1")
