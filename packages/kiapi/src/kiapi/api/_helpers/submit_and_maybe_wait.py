"""Shared sync/async job flow for generation capabilities (se, video, music).

Chat and embedding are sync-only and return their provider-native payload
directly. The generation capabilities instead:
  - accept a ``mode`` ("sync" | "async") on a single endpoint,
  - always create a Job (so it shows up in /v1/jobs and shares the single-flight
    worker), and
  - produce file artifacts referenced by ``file_id`` (see files.py).

``submit_and_maybe_wait`` centralizes that: enqueue the job's thunk, then either
return the job immediately (async, HTTP 202) or wait for it (sync), mapping the
usual failures to HTTP status codes. A sync wait that exceeds ``sync_timeout_s``
is an error (504) — no fallback to async.

**Sync content negotiation**: a sync request that produces exactly
one artifact returns that artifact's *raw bytes* by default — convenient for
``curl -o out.png .../generate`` and direct clients (``Accept: */*``). The file_id
and job_id ride along in response headers (``X-Kiapi-File-Id`` / ``X-Kiapi-Job-Id``)
so the full metadata (seed, params, timings) stays fetchable via
``GET /v1/files/{id}``. A client that sets ``Accept: application/json`` instead
gets the Job dict — as do jobs with zero or multiple artifacts (e.g. acestep
extract), and all async (202) responses.
"""

import asyncio

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response

from kiapi.core.app import AppContext
from kiapi.core.memory import MemoryBudgetError
from kiapi.core.model import UnknownModelError
from kiapi.core.setup import SetupRequiredError
from kiapi.core.worker import JobThunk, Worker

from .._settings import settings_manager


async def submit_and_maybe_wait(
    ctx: AppContext,
    worker: Worker,
    *,
    type: str,
    params: dict,
    thunk: JobThunk,
    mode: str,
    prefer_raw: bool = True,
    accept: str | None = None,
) -> Response:
    """Run a generation job. Returns the artifact bytes (sync, single artifact,
    non-JSON Accept), the job dict (sync otherwise), or {job_id,...} (async)."""
    settings = settings_manager.get_settings()

    job = ctx.job_store.create(type=type, params=params)
    fut = await worker.submit(job, thunk)

    if mode == "async":
        return JSONResponse(
            status_code=202,
            content={"job_id": job.id, "type": job.type, "status": job.status},
        )

    try:
        await asyncio.wait_for(fut, timeout=settings.sync_timeout_s)
    except TimeoutError:
        raise HTTPException(  # noqa: B904
            status_code=504,
            detail=f"{type} job {job.id} exceeded sync timeout "
            f"({settings.sync_timeout_s}s); it keeps running — poll /v1/jobs/{job.id}",
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except SetupRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except MemoryBudgetError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except Exception as exc:
        if exc.__class__.__name__ in (
            "MediaError",
            "CapabilityError",
            "ValidationError",
        ):
            raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
        raise HTTPException(status_code=500, detail=f"{type} failed: {exc}")  # noqa: B904

    # The worker mutates this same Job instance in place, so it is now updated.

    # Sync content negotiation: return the single artifact's raw bytes unless the
    # client asked for JSON (or there isn't exactly one artifact).
    if prefer_raw and not _wants_json(accept) and len(job.artifacts) == 1:
        raw = _raw_response(ctx, job, job.artifacts[0])
        if raw is not None:
            return raw

    return JSONResponse(status_code=200, content=job.to_dict())


def _wants_json(accept: str | None) -> bool:
    return "application/json" in (accept or "").lower()


def _raw_response(ctx: AppContext, job, file_id: str) -> Response | None:  # type: ignore
    """Build a raw-bytes FileResponse for a single artifact, or None if the file
    can't be resolved (caller falls back to JSON)."""
    rec = ctx.file_store.get(file_id)
    if rec is None:
        return None
    return FileResponse(
        rec.path,
        media_type=rec.content_type,
        filename=rec.filename,
        headers={"X-Kiapi-File-Id": rec.file_id, "X-Kiapi-Job-Id": job.id},
    )
