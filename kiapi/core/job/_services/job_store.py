import threading
from typing import Any

from .._models.job import Job
from .._types.job_id import JobID
from .._types.job_type import JobType


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[JobID, Job] = {}
        self._lock = threading.Lock()

    def create(self, type: JobType, params: dict[str, Any] | None = None) -> Job:
        job = Job(type=type, params=params or {})
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: JobID) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def delete(self, job_id: JobID) -> Job | None:
        """A running job cannot be interrupted (MLX/generation is not
        preemptible) — deleting it just forgets it once it finishes. Queued jobs
        are effectively canceled."""
        with self._lock:
            return self._jobs.pop(job_id, None)
