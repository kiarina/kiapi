from fastapi import APIRouter

from kiapi.api import REQUIRE_AUTH
from kiapi.core.model import model_registry
from kiapi.core.setup import SetupManager

from ._helpers.build_setup_response import build_setup_response
from ._views.setup_response import SetupResponse

router = APIRouter(prefix="/v1/setup", dependencies=REQUIRE_AUTH)


@router.get("", response_model=SetupResponse)
def get_setup() -> SetupResponse:
    """List every model with its setup state, like `kiapi status`.

    The server never downloads or removes resources itself. For a missing
    resource, run its activate_command in a terminal, then call this endpoint
    again. Checking Docker images and Python environments runs local commands,
    so a call can take a few seconds.
    """
    return build_setup_response(model_registry.list_specs(), SetupManager())
