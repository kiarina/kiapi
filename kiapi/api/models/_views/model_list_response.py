from pydantic import BaseModel, Field

from .._schemas.openai_model_spec import OpenAIModelSpec


class ModelListResponse(BaseModel):
    object: str = Field(
        default="list",
        description="OpenAI-style list envelope marker.",
        examples=["list"],
    )
    data: list[OpenAIModelSpec] = Field(
        default_factory=list,
        description="Chat models available via the OpenAI-compatible /v1/models endpoint.",
    )
