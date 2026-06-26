from pydantic import BaseModel, Field


class OpenAIModelSpec(BaseModel):
    """An OpenAI-compatible model spec (one entry in a model list)."""

    id: str = Field(
        ...,
        description="Model name to pass in the chat request model field.",
        examples=["qwen3-omni"],
    )
    object: str = Field(
        default="model",
        description="OpenAI-compatible object marker.",
        examples=["model"],
    )
    created: int = Field(
        ...,
        description="Unix timestamp (seconds) for when the model became available.",
        examples=[1735689600],
    )
    owned_by: str = Field(
        default="kiapi",
        description="Owner marker for OpenAI-compatible model lists.",
        examples=["kiapi"],
    )
