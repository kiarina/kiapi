from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.memory_budget_error import MemoryBudgetError
    from ._helpers.create_memory_manager import create_memory_manager
    from ._schemas.memory_stats import MemoryStats
    from ._schemas.resident_model_stats import ResidentModelStats
    from ._services.memory_manager import MemoryManager
    from ._settings import MemorySettings, settings_manager

__all__ = [
    "MemoryBudgetError",
    "MemoryManager",
    "MemorySettings",
    "MemoryStats",
    "ResidentModelStats",
    "create_memory_manager",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "MemoryBudgetError": "._exceptions.memory_budget_error",
        "MemoryManager": "._services.memory_manager",
        "MemorySettings": "._settings",
        "MemoryStats": "._schemas.memory_stats",
        "ResidentModelStats": "._schemas.resident_model_stats",
        "create_memory_manager": "._helpers.create_memory_manager",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
