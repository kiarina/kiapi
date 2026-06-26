"""The single-flight worker: one dedicated thread runs every job, one at a time
(MLX thread-affinity + sound memory budgeting). See :mod:`._services.worker`.

Public surface (unchanged from the former ``core/worker.py``): :class:`Worker`,
:data:`JobThunk`.
"""

from ._helpers.create_worker import create_worker
from ._services.worker import Worker
from ._settings import WorkerSettings, settings_manager
from ._types.job_thunk import JobThunk

__all__ = [
    # ._types
    "JobThunk",
    # ._services
    "Worker",
    # ._settings
    "WorkerSettings",
    # ._helpers
    "create_worker",
    "settings_manager",
]
