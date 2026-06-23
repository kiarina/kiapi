from fastapi import APIRouter, Depends

from kiapi.api import get_ctx, get_worker
from kiapi.core.app import AppContext
from kiapi.core.worker import Worker

from ._views.health_response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> dict:
    """Inspect server readiness, queue depth, and resident model memory.

    Use this endpoint to see whether warmup has finished, how many jobs are
    queued behind the single-flight worker, and which resident models currently
    count against the global memory budget.
    """
    return {
        "status": "ok",
        "warm": worker.warm,
        "queue_len": worker.queue.qsize(),
        "memory": ctx.memory_manager.stats(),
    }
