"""Unified job model + in-memory job store. Every generation (sync or async) is
a Job; sync waits for it, async returns its id. Jobs reset on restart.

Public surface (was ``core/jobs.py``): :class:`Job`, :class:`JobStore`,
:class:`JobStatus`, :class:`ProgressReporter`, :func:`creep_progress`.
"""

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
