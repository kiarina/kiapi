from pydantic import BaseModel, Field


class JobDeleteResponse(BaseModel):
    deleted: bool = Field(
        ...,
        description="True when the job was removed from the in-memory job store.",
        examples=[True],
    )
    job_id: str = Field(
        ...,
        description="Deleted job id.",
        examples=["job_0123456789abcdef"],
    )
    was_running: bool = Field(
        ...,
        description="True if the job was running when deleted. Running jobs cannot be interrupted; deletion only forgets the record.",
        examples=[False],
    )
