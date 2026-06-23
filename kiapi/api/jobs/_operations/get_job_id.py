from typing import Annotated

from fastapi import Path

from kiapi.core.job import JobID


def get_job_id(
    job_id: Annotated[
        str,
        Path(
            pattern=r"^job_[0-9a-f]+$",
            description="In-memory job id returned by async or sync inference requests.",
            examples=["job_0123456789abcdef"],
        ),
    ],
) -> JobID:
    return job_id
