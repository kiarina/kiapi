import logging

import psutil  # type: ignore[import-untyped]

from .._settings import MemorySettings

_GB = 1024**3
logger = logging.getLogger(__name__)


def log_memory_limit(settings: MemorySettings, effective_limit_gb: float) -> None:
    memory = psutil.virtual_memory()
    total_gb = memory.total / _GB
    available_gb = memory.available / _GB
    mode = "configured" if settings.memory_limit_gb is not None else "auto"

    logger.info(
        "memory budget %s: effective %.1f GB (total %.1f GB, available %.1f GB)",
        mode,
        effective_limit_gb,
        total_gb,
        available_gb,
    )
    if available_gb < effective_limit_gb:
        logger.warning(
            "memory budget %.1f GB exceeds currently available memory %.1f GB",
            effective_limit_gb,
            available_gb,
        )
