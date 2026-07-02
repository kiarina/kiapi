"""The single-flight worker: one dedicated thread runs every job, one at a time
(MLX thread-affinity + sound memory budgeting). See :mod:`._services.worker`.

Public surface (unchanged from the former ``core/worker.py``): :class:`Worker`,
:data:`JobThunk`.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.create_worker import create_worker
    from ._services.worker import Worker
    from ._settings import WorkerSettings, settings_manager
    from ._types.job_thunk import JobThunk

__all__ = [
    "JobThunk",
    "Worker",
    "WorkerSettings",
    "create_worker",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "JobThunk": "._types.job_thunk",
        "Worker": "._services.worker",
        "WorkerSettings": "._settings",
        "create_worker": "._helpers.create_worker",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
