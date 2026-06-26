from kiapi.capabilities import ValidationError

from .._operations.validate_common import validate_common
from .._settings import settings_manager
from .._views.edit_request import EditRequest


def validate_edit(req: EditRequest, *, variant: str) -> None:
    settings = settings_manager.get_settings()
    validate_common(req, settings, variant=variant)
    if not req.images:
        raise ValidationError("edit requires at least one image")
