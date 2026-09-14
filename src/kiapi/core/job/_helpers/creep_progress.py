"""Synthetic 'liveness' progress for jobs whose backend exposes no per-step hook.

Some generation backends (notably ltx2's ``mlx_video.generate_video``, which only
drives its own internal rich progress bar) give us no way to observe denoising
steps — unlike mflux, which offers a callback registry (see capabilities'
``attach_mflux_progress``). A polling client, typically an LLM agent, reads a job
whose ``progress`` never moves as possibly hung and may stop waiting.

For those backends we creep the reported fraction forward on a piecewise-linear
schedule (see :func:`_scheduled_fraction`) — constant, easy-to-read rates rather
than a smooth curve. This is a deliberate fiction: it signals 'alive and working',
not real completion; the genuine terminal 1.0 still comes only from
:meth:`Job.mark_succeeded`.

The job's worker thread is blocked inside the backend call while this runs, so a
daemon thread does the ticking. ContextVars don't cross threads, so it captures
the worker thread's bound :class:`ProgressReporter` up front and pushes updates
through it — the same throttling and job wiring apply.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from .._services.progress_reporter import ProgressReporter


def _scheduled_fraction(
    elapsed: float,
    *,
    eta_s: float,
    cap: float,
    ramp_frac: float,
    ramp_rate: float,
    mid_frac: float,
    mid_fallback_rate: float,
    tail_rate: float,
) -> float:
    """The reported fraction at ``elapsed`` seconds — three constant-rate phases:

    1. **ramp** — linear from 0 to ``ramp_frac`` at a *fixed* ``ramp_rate`` per
       second (e.g. 0 → 0.20 at 0.5%/s, reaching 0.20 after 40s). The rate is
       always honoured, even for a short ``eta_s``, so the start is always a gentle
       crawl — easier to wait on than an immediate jump.
    2. **mid** — linear from ``ramp_frac`` to ``mid_frac``. Normally paced to hit
       ``mid_frac`` exactly at ``eta_s``; but if the ramp has already consumed
       ``eta_s`` (``eta_s <= ramp duration``), there is no room left to pace to, so
       it falls back to the fixed ``mid_fallback_rate`` per second (e.g. 1%/s).
    3. **tail** — linear from ``mid_frac`` upward at the slow ``tail_rate`` per
       second, clamped at ``cap`` — the overrun crawl.
    """
    knee_t = ramp_frac / ramp_rate  # fixed: guarantees the slow start
    if elapsed <= knee_t:
        return min(cap, ramp_rate * elapsed)

    if eta_s > knee_t:
        mid_end_t = eta_s  # room to pace: land on mid_frac exactly at eta
    else:
        mid_end_t = knee_t + (mid_frac - ramp_frac) / mid_fallback_rate

    if elapsed <= mid_end_t:
        fraction = ramp_frac + (mid_frac - ramp_frac) * (elapsed - knee_t) / (
            mid_end_t - knee_t
        )
    else:
        fraction = mid_frac + tail_rate * (elapsed - mid_end_t)
    return min(cap, max(0.0, fraction))


@contextmanager
def creep_progress(
    *,
    eta_s: float,
    cap: float = 0.999,
    label: str = "generating",
    interval_s: float = 1.0,
    ramp_frac: float = 0.20,
    ramp_rate: float = 0.005,
    mid_frac: float = 0.80,
    mid_fallback_rate: float = 0.01,
    tail_rate: float = 0.0005,
) -> Iterator[None]:
    """Tick synthetic progress on a piecewise-linear schedule while the block runs.

    The fraction follows :func:`_scheduled_fraction`: a fixed-rate ramp to
    ``ramp_frac`` (always a gentle start), an even climb to ``mid_frac`` timed to
    land at ``eta_s`` (or a fixed ``mid_fallback_rate`` if ``eta_s`` is already
    spent), then a slow ``tail_rate`` crawl up to ``cap``. ``eta_s`` only sets the
    pace, never the ceiling, so a job that overruns keeps inching forward in the
    tail phase rather than stalling. ``eta_s <= 0`` disables creeping entirely.
    """
    reporter = ProgressReporter.current()
    if eta_s <= 0:
        yield
        return

    stop = threading.Event()
    t0 = time.monotonic()

    def _tick() -> None:
        while not stop.wait(interval_s):
            fraction = _scheduled_fraction(
                time.monotonic() - t0,
                eta_s=eta_s,
                cap=cap,
                ramp_frac=ramp_frac,
                ramp_rate=ramp_rate,
                mid_frac=mid_frac,
                mid_fallback_rate=mid_fallback_rate,
                tail_rate=tail_rate,
            )
            reporter.update(fraction, label)

    thread = threading.Thread(target=_tick, name="kiapi-progress-creep", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2.0)
