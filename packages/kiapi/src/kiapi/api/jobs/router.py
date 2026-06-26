"""Jobs API: list / get / delete. Every generation (sync or async) is a job."""

from fastapi import APIRouter, Depends, HTTPException

from kiapi.api import REQUIRE_AUTH, get_ctx
from kiapi.core.app import AppContext
from kiapi.core.job import Job, JobID, JobStatus

from ._operations.get_job_id import get_job_id
from ._views.job_delete_response import JobDeleteResponse
from ._views.job_list_response import JobListResponse

router = APIRouter(prefix="/v1/jobs", dependencies=REQUIRE_AUTH)


@router.get("", response_model=JobListResponse)
async def list_jobs(ctx: AppContext = Depends(get_ctx)) -> dict:
    """List in-memory jobs.

    Every generation request creates a job, including sync requests. Jobs are
    useful for progress polling, result inspection, and discovering artifact
    file_ids. They are not persisted across process restarts.
    """
    return {"object": "list", "data": [j.to_dict() for j in ctx.job_store.list_all()]}


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: JobID = Depends(get_job_id),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    """Get a job's status, progress, result, and artifacts.

    Poll this endpoint after an async response or after a sync request times
    out. When status is succeeded, artifact file ids can be downloaded through
    the Files API.
    """
    job = ctx.job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job {job_id!r}")
    return job.to_dict()


@router.delete("/{job_id}", response_model=JobDeleteResponse)
async def delete_job(
    job_id: JobID = Depends(get_job_id),
    ctx: AppContext = Depends(get_ctx),
) -> dict:
    """Remove a job record from the in-memory store.

    Queued jobs are forgotten and effectively canceled. A running job cannot be
    interrupted; deleting it only removes the record, and generated files are
    managed separately by the Files API.
    """
    job = ctx.job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job {job_id!r}")
    # A running job cannot be interrupted (MLX/generation is not preemptible);
    # deleting it just forgets it. Queued jobs are effectively canceled.
    running = job.status == JobStatus.RUNNING
    ctx.job_store.delete(job_id)
    return {"deleted": True, "job_id": job_id, "was_running": running}
