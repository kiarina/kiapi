from pydantic import BaseModel, Field

from kiapi.core.job import Job


class JobListResponse(BaseModel):
    object: str = Field(
        default="list",
        description="OpenAI-style list envelope marker.",
        examples=["list"],
    )
    data: list[Job] = Field(
        default_factory=list,
        description="Jobs currently retained in the in-memory job store.",
    )
