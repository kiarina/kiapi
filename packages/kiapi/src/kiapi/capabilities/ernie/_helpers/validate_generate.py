from .._operations.validate_common import validate_common
from .._settings import settings_manager
from .._views.generate_request import GenerateRequest


def validate_generate(req: GenerateRequest, *, variant: str) -> None:
    settings = settings_manager.get_settings()
    validate_common(req, settings, variant=variant)
