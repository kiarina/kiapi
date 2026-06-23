import psutil  # type: ignore[import-untyped]

from .._settings import MemorySettings

_GB = 1024**3
_AUTO_MEMORY_LIMIT_RATIO = 0.8


def resolve_effective_memory_limit_gb(settings: MemorySettings) -> float:
    if settings.memory_limit_gb is not None:
        return settings.memory_limit_gb

    return float(psutil.virtual_memory().total) / _GB * _AUTO_MEMORY_LIMIT_RATIO
