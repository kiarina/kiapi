import logging
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)


def log_apc_result(payload: SimpleNamespace, model_name: str, result: Any) -> None:
    manager = getattr(payload, "apc_manager", None)
    if manager is None or result is None:
        return
    logger.info(
        "chat APC model=%s prompt_tokens=%s cached_tokens=%s prompt_tps=%.2f "
        "peak_memory_gb=%.2f resident_bytes=%s stats=%s",
        model_name,
        getattr(result, "prompt_tokens", 0),
        getattr(result, "cached_tokens", 0),
        float(getattr(result, "prompt_tps", 0.0)),
        float(getattr(result, "peak_memory", 0.0)),
        manager.resident_bytes(),
        manager.stats_snapshot(),
    )
