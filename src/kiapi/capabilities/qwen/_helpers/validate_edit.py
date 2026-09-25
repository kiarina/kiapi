from kiapi.capabilities import ValidationError

from .._constants.image_21 import IMAGE_21_VARIANT
from .._operations.validate_common import validate_common
from .._settings import settings_manager
from .._views.edit_request import EditRequest

_IMAGE_21_MAX_IMAGES = 10


def validate_edit(req: EditRequest, *, variant: str) -> None:
    settings = settings_manager.get_settings()
    validate_common(req, settings, role="edit", variant=variant)
    if not req.images:
        raise ValidationError("edit requires at least one image")
    if variant == IMAGE_21_VARIANT and len(req.images) > _IMAGE_21_MAX_IMAGES:
        raise ValidationError(
            f"image-2.1 accepts at most {_IMAGE_21_MAX_IMAGES} reference images"
        )
