import time

from fastapi import APIRouter

from kiapi.core.model import model_registry

from ._schemas.openai_model_spec import OpenAIModelSpec
from ._views.model_list_response import ModelListResponse

router = APIRouter()

# Stable per-process timestamp used for the OpenAI-compatible ``created`` field;
# kiapi models don't carry a real creation date, so we report server start.
_CREATED = int(time.time())


@router.get("/v1/models", response_model=ModelListResponse)
async def list_openai_compatible_chat_models() -> ModelListResponse:
    """List OpenAI-compatible chat models.

    Returns the OpenAI /v1/models shape so OpenAI chat clients work unchanged.
    Other capabilities expose richer, family-specific model lists at
    /v1/{domain}/{family}/models.
    """
    data = [
        OpenAIModelSpec(id=spec.name, created=_CREATED)
        for spec in model_registry.list_specs("chat")
    ]
    return ModelListResponse(data=data)
