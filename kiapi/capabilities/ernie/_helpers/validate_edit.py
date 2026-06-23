from kiapi.capabilities import ValidationError

from .._operations.validate_common import validate_common
from .._settings import settings_manager
from .._views.edit_request import EditRequest


def validate_edit(req: EditRequest, *, variant: str) -> None:
    settings = settings_manager.get_settings()
    validate_common(req, settings, variant=variant)
    if not 0 <= req.image_strength <= 1:
        raise ValidationError("image_strength must be in 0..1")
    width = req.width if req.width is not None else settings.default_width
    height = req.height if req.height is not None else settings.default_height
    if settings.edit_require_square and width != height:
        raise ValidationError(
            "ERNIE edit currently requires square width/height; set "
            "KIAPI_ERNIE_EDIT_REQUIRE_SQUARE=0 to disable this guard"
        )
