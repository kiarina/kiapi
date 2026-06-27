from fastapi import APIRouter, Depends

from kiapi.api import get_ctx, get_relay_runner, get_worker
from kiapi.core.app import AppContext
from kiapi.core.worker import Worker
from kiapi_relay import RelayRunner

from ._views.health_response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
    relay_runner: RelayRunner | None = Depends(get_relay_runner),
) -> dict:
    """Inspect server readiness, queue depth, resident model memory, and relay.

    Use this endpoint to see whether warmup has finished, how many jobs are
    queued behind the single-flight worker, which resident models currently
    count against the global memory budget, and whether the relay started with
    the server is running.
    """
    return {
        "status": "ok",
        "warm": worker.warm,
        "queue_len": worker.queue.qsize(),
        "memory": ctx.memory_manager.stats(),
        "relay": relay_runner.status() if relay_runner is not None else None,
    }
