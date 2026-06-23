"""Ambient progress reporting for the running job.

kiapi runs exactly one job at a time on one worker thread (see core/worker), so
"the progress of the currently running job" is a well-defined ambient rather than
something every call site must thread through by hand. The worker binds a
:class:`ProgressReporter` for the job it is about to run; capability code reaches
it with :meth:`ProgressReporter.current` and calls :meth:`update` / :meth:`step`
to push coarse progress onto the :class:`Job` (surfaced by /v1/jobs).

A reporter bound to no job (the default outside a running job) is a silent no-op,
so capability code can call ``ProgressReporter.current().update(...)``
unconditionally. Updates are throttled (time + delta) so a hot denoising loop
calling ``step`` per iteration stays cheap; the terminal ``1.0`` from
``Job.mark_succeeded`` is what guarantees a clean final value.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from contextvars import ContextVar
from typing import Self, TypeVar

from .._models.job import Job

T = TypeVar("T")


class ProgressReporter:
    _current: ContextVar[ProgressReporter | None] = ContextVar(
        "kiapi_progress_reporter", default=None
    )

    def __init__(
        self,
        job: Job | None = None,
        *,
        min_interval_s: float = 0.5,
        min_delta: float = 0.01,
    ) -> None:
        self._job = job
        self._min_interval_s = min_interval_s
        self._min_delta = min_delta
        self._last_at = 0.0
        self._last_fraction = -1.0

    def update(self, fraction: float, label: str | None = None) -> None:
        if self._job is None:
            return

        now = time.monotonic()
        forced = label is not None or fraction >= 1.0

        if not forced:
            if now - self._last_at < self._min_interval_s:
                return
            if abs(fraction - self._last_fraction) < self._min_delta:
                return

        self._last_at = now
        self._last_fraction = fraction
        self._job.update_progress(fraction, label)

    def step(self, i: int, total: int, label: str | None = None) -> None:
        if total > 0:
            self.update(i / total, label)

    @classmethod
    def current(cls) -> Self:
        reporter = cls._current.get()
        return reporter if isinstance(reporter, cls) else cls()

    def run_bound(self, fn: Callable[[], T]) -> T:
        token = self._current.set(self)

        try:
            return fn()
        finally:
            self._current.reset(token)
