"""Unified job model.

Every generation in kiapi — sync or async, chat or video — is a Job. Sync
requests create a job, wait for it, and return its result; async requests create
a job and return its id immediately. This gives one consistent place to inspect
work in flight and one consistent result shape.

``result`` is a free-form dict whose shape depends on ``type`` (the caller
dispatches on ``type``); ``artifacts`` lists file_ids produced (see core/file).
Jobs are in-memory only and reset on restart; artifacts are Files API entries
that can outlive jobs while their files remain on disk.
"""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from kiapi.core.file import FileID

from .._enums.job_status import JobStatus
from .._types.job_id import JobID
from .._types.job_result import JobResult
from .._types.job_type import JobType


class Job(BaseModel):
    type: JobType = Field(
        ...,
        description="Job type. Use this to interpret the capability-specific result payload.",
        examples=["zimage"],
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Request parameters captured for inspection and reproducibility. Secret or large media payloads may be omitted or redacted by endpoints.",
    )
    id: JobID = Field(
        default_factory=lambda: f"job_{uuid.uuid4().hex}",
        description="In-memory job id. Jobs are cleared when the kiapi process restarts.",
        examples=["job_0123456789abcdef"],
    )
    status: JobStatus = Field(
        default=JobStatus.QUEUED,
        description="Job lifecycle state: queued, running, succeeded, failed, or canceled.",
        examples=["succeeded"],
    )
    result: JobResult | None = Field(
        default=None,
        description="Capability-specific result metadata. Completed generation jobs usually also expose produced file ids in artifacts.",
        examples=[{"file_id": "file_0123456789abcdef", "image_bytes": 123456}],
    )
    artifacts: list[FileID] = Field(
        default_factory=list,
        description="File ids produced by the job. Use GET /v1/files/{file_id} for metadata or /download for bytes.",
        examples=[["file_0123456789abcdef"]],
    )
    error: str | None = Field(
        default=None,
        description="Error message when status is failed; otherwise null.",
        examples=["model 'turbo' is not activated"],
    )
    created_at: float = Field(
        default_factory=lambda: time.time(),
        description="Unix timestamp when the job was created.",
        examples=[1766200000.0],
    )
    started_at: float | None = Field(
        default=None,
        description="Unix timestamp when the worker started the job, or null while queued.",
        examples=[1766200001.0],
    )
    finished_at: float | None = Field(
        default=None,
        description="Unix timestamp when the job reached a terminal state, or null while queued/running.",
        examples=[1766200030.0],
    )
    progress: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Best-effort completion fraction in [0.0, 1.0]. Null means the job has not reported progress.",
        examples=[0.42],
    )
    progress_label: str = Field(
        default="queued",
        description="Short human-readable phase label such as queued, running, denoising, saving, or done.",
        examples=["denoising"],
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING
        self.started_at = time.time()
        self.progress = 0.0
        self.progress_label = "running"

    def update_progress(self, fraction: float, label: str | None = None) -> None:
        self.progress = min(1.0, max(0.0, fraction))

        if label is not None:
            self.progress_label = label

    def mark_succeeded(self, result: JobResult, artifacts: list[FileID]) -> None:
        self.status = JobStatus.SUCCEEDED
        self.result = result
        self.artifacts = artifacts
        self.progress = 1.0
        self.progress_label = "done"
        self.finished_at = time.time()

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.finished_at = time.time()

    def mark_canceled(self) -> None:
        self.status = JobStatus.CANCELED
        self.finished_at = time.time()
