"""Unified job model + in-memory job store. Every generation (sync or async) is
a Job; sync waits for it, async returns its id. Jobs reset on restart.

Public surface (was ``core/jobs.py``): :class:`Job`, :class:`JobStore`,
:class:`JobStatus`, :class:`ProgressReporter`, :func:`creep_progress`.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._enums.job_status import JobStatus
    from ._helpers.creep_progress import creep_progress
    from ._models.job import Job
    from ._services.job_store import JobStore
    from ._services.progress_reporter import ProgressReporter
    from ._types.job_id import JobID
    from ._types.job_result import JobResult

__all__ = [
    "Job",
    "JobID",
    "JobResult",
    "JobStatus",
    "JobStore",
    "ProgressReporter",
    "creep_progress",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "Job": "._models.job",
        "JobID": "._types.job_id",
        "JobResult": "._types.job_result",
        "JobStatus": "._enums.job_status",
        "JobStore": "._services.job_store",
        "ProgressReporter": "._services.progress_reporter",
        "creep_progress": "._helpers.creep_progress",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
