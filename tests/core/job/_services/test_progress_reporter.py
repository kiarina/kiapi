from kiapi.core.job import Job, ProgressReporter


def test_job_update_progress_clamps_and_keeps_label() -> None:
    job = Job(type="chat")
    job.update_progress(0.4, "denoising")
    assert job.progress == 0.4
    assert job.progress_label == "denoising"

    # Out-of-range fractions are clamped; an omitted label is preserved.
    job.update_progress(1.5)
    assert job.progress == 1.0
    assert job.progress_label == "denoising"

    job.update_progress(-2.0)
    assert job.progress == 0.0


def test_initial_state_is_queued_with_no_progress() -> None:
    job = Job(type="chat")
    assert job.progress is None
    assert job.progress_label == "queued"


def test_lifecycle_sets_progress_label_and_fraction() -> None:
    job = Job(type="chat")

    job.mark_running()
    assert job.progress == 0.0
    assert job.progress_label == "running"

    job.mark_succeeded(result={"ok": True}, artifacts=[])
    assert job.progress == 1.0
    assert job.progress_label == "done"


def test_null_reporter_is_silent() -> None:
    # current() outside a bound job is a no-op and must not raise.
    reporter = ProgressReporter.current()
    reporter.update(0.5, "x")
    reporter.step(1, 2)


def test_reporter_pushes_progress_onto_bound_job() -> None:
    job = Job(type="chat")
    reporter = ProgressReporter(job, min_interval_s=0.0, min_delta=0.0)
    reporter.step(3, 4, "denoising")
    assert job.progress == 0.75
    assert job.progress_label == "denoising"


def test_reporter_throttles_unforced_updates() -> None:
    job = Job(type="chat")
    reporter = ProgressReporter(job, min_interval_s=1000.0, min_delta=0.01)
    reporter.update(0.1, "running")  # forced by label -> applied
    assert job.progress == 0.1
    reporter.update(0.2)  # throttled by interval -> dropped
    assert job.progress == 0.1
    reporter.update(1.0)  # completion always flushes
    assert job.progress == 1.0


def test_run_bound_installs_and_restores_current() -> None:
    job = Job(type="chat")
    reporter = ProgressReporter(job, min_interval_s=0.0, min_delta=0.0)

    def body() -> str:
        ProgressReporter.current().update(0.5, "mid")
        return "ok"

    assert reporter.run_bound(body) == "ok"
    assert job.progress == 0.5
    # Binding is restored after the call returns.
    assert ProgressReporter.current() is not reporter
