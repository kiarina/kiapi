"""Embedding API: OpenAI-compatible ``POST /v1/embeddings`` (sync only).

Like chat, still a job internally (shows up in /v1/jobs, shares the single-flight
worker), but no async mode: the caller always gets the vector back. A sync wait
that exceeds ``sync_timeout_s`` is an error (504).
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from kiapi.api import (
    REQUIRE_AUTH,
    get_ctx,
    get_worker,
    register_capability_endpoints,
)
from kiapi.api._settings import settings_manager
from kiapi.capabilities.embedding import EmbedRequest, handle_embed
from kiapi.core.app import AppContext
from kiapi.core.memory import MemoryBudgetError
from kiapi.core.model import UnknownModelError
from kiapi.core.setup import SetupRequiredError
from kiapi.core.worker import Worker

from ._views.embedding_response import EmbeddingResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/embeddings",
    response_model=EmbeddingResponse,
    responses={
        400: {
            "description": (
                "Unknown model, empty or oversized input, unsupported modality, "
                "or unsupported dimensions."
            )
        },
        503: {"description": "Model not set up, or memory budget exceeded."},
        504: {"description": "Sync timeout exceeded; the job keeps running."},
    },
)
async def embeddings(
    req: EmbedRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> dict:
    """Create embeddings, following OpenAI's embeddings API.

    `input` takes a string or an array, and `data` returns one L2-normalized,
    last-token-pooled vector per input. Multimodal models also accept
    `{text, image}` objects. The resolved `model` (see GET /v1/embedding/models)
    determines which modalities are accepted.

    Embedding runs as a single-flight job, so it appears in /v1/jobs and is
    serialized with all other generation, but there is no async mode: the caller
    always waits for the vectors. A wait that exceeds the sync timeout returns 504
    while the job keeps running and can be polled at /v1/jobs/{id}.
    """
    settings = settings_manager.get_settings()

    job = ctx.job_store.create(type="embedding", params={"model": req.model})
    fut = await worker.submit(job, lambda: handle_embed(ctx, req))

    try:
        return await asyncio.wait_for(fut, timeout=settings.sync_timeout_s)
    except TimeoutError:
        raise HTTPException(  # noqa: B904
            status_code=504,
            detail=f"embedding job {job.id} exceeded sync timeout "
            f"({settings.sync_timeout_s}s); poll /v1/jobs/{job.id}",
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except SetupRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except MemoryBudgetError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except Exception as exc:
        if exc.__class__.__name__ in ("MediaError", "CapabilityError"):
            raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
        raise HTTPException(status_code=500, detail=f"embedding failed: {exc}")  # noqa: B904


register_capability_endpoints(router, name="embedding", base_path="/v1/embedding")
