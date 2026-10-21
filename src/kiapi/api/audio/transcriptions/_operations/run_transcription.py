"""Run one transcription as a job on the single worker and wait for its result."""

import asyncio
import shutil
from pathlib import Path

from fastapi import HTTPException

from kiapi.api import settings_manager
from kiapi.capabilities import CapabilityError
from kiapi.capabilities.transcriptions import (
    TranscriptionRequest,
    ValidationError,
    handle_transcription,
)
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.memory import MemoryBudgetError
from kiapi.core.model import UnknownModelError
from kiapi.core.setup import SetupRequiredError
from kiapi.core.worker import Worker


async def run_transcription(
    ctx: AppContext,
    worker: Worker,
    req: TranscriptionRequest,
    audio_path: Path,
    *,
    work_dir: Path | None = None,
) -> JobResult:
    """Errors become HTTP errors; ``work_dir`` is removed once the job ends."""

    def thunk() -> tuple[JobResult, list[FileID]]:
        try:
            return handle_transcription(ctx, req, audio_path)
        finally:
            if work_dir is not None:
                shutil.rmtree(work_dir, ignore_errors=True)

    timeout = settings_manager.get_settings().sync_timeout_s
    job = ctx.job_store.create(
        type="transcriptions",
        params=req.model_dump(mode="json", exclude={"prompt"}),
    )
    fut = await worker.submit(job, thunk)
    try:
        return await asyncio.wait_for(asyncio.shield(fut), timeout=timeout)
    except TimeoutError:
        raise HTTPException(  # noqa: B904
            status_code=504,
            detail=f"transcription job {job.id} exceeded sync timeout "
            f"({timeout}s); it keeps running - poll /v1/jobs/{job.id}",
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except (SetupRequiredError, MemoryBudgetError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    except CapabilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"transcription failed: {exc}")  # noqa: B904
