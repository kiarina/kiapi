from pydantic import BaseModel, Field

from kiapi.core.memory import MemoryStats


class HealthResponse(BaseModel):
    status: str = Field(
        ...,
        description="Service health marker. The value is ok when the API process is accepting requests.",
        examples=["ok"],
    )
    warm: bool = Field(
        ...,
        description="Whether startup warmup has finished. Warmup may skip models that are not activated.",
        examples=[True],
    )
    queue_len: int = Field(
        ...,
        ge=0,
        description="Number of jobs waiting in the single-flight worker queue.",
        examples=[0],
    )
    memory: MemoryStats = Field(
        ...,
        description="Resident model memory budget and loaded model snapshot.",
    )
