from pydantic import BaseModel, Field

from kiapi.core.job import JobStatus


class AsyncJobResponse(BaseModel):
    job_id: str = Field(
        ...,
        description="In-memory job id. Poll GET /v1/jobs/{job_id} to inspect status, progress, result, and artifacts.",
        examples=["job_0123456789abcdef"],
    )
    type: str = Field(
        ...,
        description="Job type. Generation APIs use values such as zimage, flux2-edit, or acestep-extract.",
        examples=["zimage"],
    )
    status: JobStatus = Field(
        ...,
        description="Initial job status. Async responses are normally queued unless the worker starts immediately.",
        examples=["queued"],
    )
