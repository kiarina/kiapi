from types import SimpleNamespace
from typing import Any

from kiapi.capabilities import attach_mflux_progress
from kiapi.core.job import Job, ProgressReporter


class _FakeRegistry:
    """Minimal stand-in for mflux's CallbackRegistry: register() routes anything
    with call_in_loop onto the in_loop list (the behavior attach relies on)."""

    def __init__(self) -> None:
        self.in_loop: list[Any] = []

    def register(self, callback: Any) -> None:
        if hasattr(callback, "call_in_loop"):
            self.in_loop.append(callback)


def _attached_callback() -> Any:
    """Attach to a fresh model and return the registered in-loop callback."""
    model = SimpleNamespace(callbacks=_FakeRegistry())
    attach_mflux_progress(model)
    return model.callbacks.in_loop[0]


def _fake_time_steps(n: int, total: int | None) -> SimpleNamespace:
    # Mimics the tqdm passed to call_in_loop: .n completed before this step.
    return SimpleNamespace(n=n, total=total)


def test_callback_reports_step_fraction_to_bound_job() -> None:
    job = Job(type="image")
    cb = _attached_callback()

    def body() -> None:
        # 3rd step (n=2) of 10 -> 3/10 done.
        cb.call_in_loop(
            t=2,
            seed=0,
            prompt="x",
            latents=None,
            config=SimpleNamespace(num_inference_steps=10),
            time_steps=_fake_time_steps(2, 10),
        )

    ProgressReporter(job, min_interval_s=0.0, min_delta=0.0).run_bound(body)
    assert job.progress == 0.3
    assert job.progress_label == "denoising"


def test_callback_falls_back_to_config_when_total_missing() -> None:
    job = Job(type="image")
    cb = _attached_callback()

    def body() -> None:
        cb.call_in_loop(
            t=0,
            seed=0,
            prompt="x",
            latents=None,
            config=SimpleNamespace(num_inference_steps=4),
            time_steps=_fake_time_steps(0, None),
        )

    ProgressReporter(job, min_interval_s=0.0, min_delta=0.0).run_bound(body)
    assert job.progress == 0.25


def test_attach_is_idempotent() -> None:
    model = SimpleNamespace(callbacks=_FakeRegistry())
    attach_mflux_progress(model)
    attach_mflux_progress(model)
    assert len(model.callbacks.in_loop) == 1


def test_attach_noop_without_registry() -> None:
    # A non-mflux model (no .callbacks) must be tolerated silently.
    attach_mflux_progress(SimpleNamespace())
