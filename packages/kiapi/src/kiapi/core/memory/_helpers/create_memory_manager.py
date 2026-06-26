from .._operations.log_memory_limit import log_memory_limit
from .._operations.resolve_effective_memory_limit_gb import (
    resolve_effective_memory_limit_gb,
)
from .._services.memory_manager import MemoryManager
from .._settings import settings_manager


def create_memory_manager() -> MemoryManager:
    settings = settings_manager.get_settings()

    effective_limit_gb = resolve_effective_memory_limit_gb(settings)
    log_memory_limit(settings, effective_limit_gb)

    return MemoryManager(
        settings.model_copy(update={"memory_limit_gb": effective_limit_gb})
    )
