"""Unit tests for the synthetic 'liveness' progress creep (CPU-only)."""

import time
from itertools import pairwise

from kiapi.core.job import Job, ProgressReporter, creep_progress
from kiapi.core.job._helpers.creep_progress import _scheduled_fraction

_SCHED = {
    "eta_s": 90.0,
    "cap": 0.999,
    "ramp_frac": 0.20,
    "ramp_rate": 0.005,
    "mid_frac": 0.80,
    "mid_fallback_rate": 0.01,
    "tail_rate": 0.0005,
}


def test_schedule_phase_boundaries() -> None:
    # Ramp: 0.5%/s reaches 20% at 40s.
    assert _scheduled_fraction(0.0, **_SCHED) == 0.0
    assert _scheduled_fraction(20.0, **_SCHED) == 0.10
    assert _scheduled_fraction(40.0, **_SCHED) == 0.20
    # Mid: even climb landing exactly on 80% at eta.
    assert _scheduled_fraction(90.0, **_SCHED) == 0.80
    # Tail: 0.05%/s past eta.
    assert _scheduled_fraction(190.0, **_SCHED) == 0.80 + 0.0005 * 100


def test_schedule_is_monotonic_and_capped() -> None:
    vals = [_scheduled_fraction(t, **_SCHED) for t in range(0, 1200, 5)]
    assert all(b >= a for a, b in pairwise(vals)), vals
    assert max(vals) <= _SCHED["cap"]
    assert vals[-1] == _SCHED["cap"]  # tail reaches the ceiling and stays there


def test_schedule_keeps_moving_through_the_tail() -> None:
    # Well past eta the value must still advance every step, not freeze.
    a = _scheduled_fraction(200.0, **_SCHED)
    b = _scheduled_fraction(210.0, **_SCHED)
    assert b > a
    assert round(b - a, 5) == round(_SCHED["tail_rate"] * 10, 5)


def test_short_eta_keeps_slow_start_and_uses_fixed_mid() -> None:
    # eta shorter than the 40s ramp must NOT speed up the start: the ramp stays a
    # guaranteed 0.5%/s, then the mid phase falls back to a fixed 1%/s.
    short = {**_SCHED, "eta_s": 10.0}
    assert _scheduled_fraction(10.0, **short) == 0.05  # still 0.5%/s, not jumped
    assert _scheduled_fraction(40.0, **short) == 0.20  # ramp reaches 20% at 40s
    # mid fallback 1%/s: 20% → 80% over 60s, i.e. 50% at 70s, 80% at 100s.
    assert _scheduled_fraction(70.0, **short) == 0.50
    assert _scheduled_fraction(100.0, **short) == 0.80


def test_creep_advances_job_and_stays_below_cap() -> None:
    job = Job(type="ltx2")
    job.mark_running()
    reporter = ProgressReporter(job)

    def work() -> list[float]:
        samples: list[float] = []
        deadline = time.monotonic() + 0.6
        with creep_progress(eta_s=1.0, interval_s=0.05):
            while time.monotonic() < deadline:
                time.sleep(0.05)
                if job.progress is not None:
                    samples.append(job.progress)
        return samples

    samples = reporter.run_bound(work)
    assert samples
    assert max(samples) > 0.0
    assert max(samples) < 1.0
    assert all(b >= a for a, b in pairwise(samples)), samples


def test_eta_zero_disables_creep() -> None:
    job = Job(type="ltx2")
    job.mark_running()  # sets progress to 0.0
    reporter = ProgressReporter(job)

    def work() -> None:
        with creep_progress(eta_s=0.0, interval_s=0.02):
            time.sleep(0.2)

    reporter.run_bound(work)
    assert job.progress == 0.0, "eta_s <= 0 should leave progress untouched"


def test_creep_is_silent_without_a_bound_job() -> None:
    # No reporter bound (current() returns a job-less no-op) — must not raise.
    with creep_progress(eta_s=1.0, interval_s=0.02):
        time.sleep(0.2)


def test_terminal_value_comes_from_mark_succeeded() -> None:
    job = Job(type="ltx2")
    job.mark_running()
    reporter = ProgressReporter(job)

    def work() -> None:
        with creep_progress(eta_s=1.0, interval_s=0.02):
            time.sleep(0.2)

    reporter.run_bound(work)
    assert job.progress is not None and job.progress < 1.0
    job.mark_succeeded({}, [])
    assert job.progress == 1.0
    assert job.progress_label == "done"
