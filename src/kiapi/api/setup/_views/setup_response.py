from pydantic import BaseModel, Field

from .setup_model_state import SetupModelState
from .setup_summary import SetupSummary


class SetupResponse(BaseModel):
    object: str = Field(
        default="list",
        description="OpenAI-style list envelope marker.",
        examples=["list"],
    )
    summary: SetupSummary = Field(..., description="Totals across every model.")
    data: list[SetupModelState] = Field(
        default_factory=list,
        description="Every registered model with its setup state, ordered by domain and family.",
    )
