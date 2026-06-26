"""Worker tests run the real asyncio worker loop CPU-only.

Thunks are plain Python callables (no model load); the AppContext is wired with a
real JobStore + MemoryManager and a tmp-dir FileStore, so nothing touches GPU or
the user's home. The single dedicated thread (max_workers=1) is what we assert
on: jobs execute strictly one at a time, in submission order.
"""

import asyncio
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from kiapi.core.app import AppContext
from kiapi.core.file import FileSettings, FileStore
from kiapi.core.job import Job, JobStatus, JobStore
from kiapi.core.memory import create_memory_manager
from kiapi.core.model import ModelSpec, model_registry
from kiapi.core.setup import LocalPathResource, SetupManager
from kiapi.core.worker import Worker, WorkerSettings


@pytest.fixture
def ctx(tmp_path: Path) -> AppContext:
    return AppContext(
        memory_manager=create_memory_manager(),
        job_store=JobStore(),
        file_store=FileStore(FileSettings(files_root=str(tmp_path))),
        setup_manager=SetupManager(),
    )


def _worker(ctx: AppContext, **settings: object) -> Worker:
    base: dict[str, object] = {"ttl_sweep_interval_s": 0.0, "warmup_models": []}
    base.update(settings)
    return Worker(WorkerSettings(**base), ctx)  # type: ignore[arg-type]


async def test_submit_runs_thunk_and_resolves_future(ctx: AppContext) -> None:
    worker = _worker(ctx)
    worker.start()
    job = Job(type="chat")

    fut = await worker.submit(job, lambda: ({"text": "hi"}, ["file_1"]))
    result = await fut

    assert result == {"text": "hi"}
    assert job.status is JobStatus.SUCCEEDED
    assert job.result == {"text": "hi"}
    assert job.artifacts == ["file_1"]
    await worker.stop()


async def test_failing_thunk_marks_job_failed(ctx: AppContext) -> None:
    worker = _worker(ctx)
    worker.start()
    job = Job(type="chat")

    def boom() -> tuple[dict, list]:
        raise RuntimeError("kaboom")

    fut = await worker.submit(job, boom)
    with pytest.raises(RuntimeError, match="kaboom"):
        await fut

    assert job.status is JobStatus.FAILED
    assert job.error == "kaboom"
    await worker.stop()


async def test_jobs_run_one_at_a_time_in_order(ctx: AppContext) -> None:
    worker = _worker(ctx)
    worker.start()

    order: list[str] = []
    concurrent = 0
    max_concurrent = 0

    def make_thunk(name: str) -> Callable[[], tuple[dict, list]]:
        def thunk() -> tuple[dict, list]:
            nonlocal concurrent, max_concurrent
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            time.sleep(0.02)
            order.append(name)
            concurrent -= 1
            return {}, []

        return thunk

    futures = [
        await worker.submit(Job(type="chat"), make_thunk(name))
        for name in ("a", "b", "c")
    ]
    await asyncio.gather(*futures)

    assert order == ["a", "b", "c"]
    assert max_concurrent == 1
    await worker.stop()


async def test_warmup_without_models_sets_warm(ctx: AppContext) -> None:
    worker = _worker(ctx)
    assert worker.warm is False

    await worker.warmup()

    assert worker.warm is True


async def test_warmup_skips_unactivated_model(ctx: AppContext, tmp_path: Path) -> None:
    module = ModuleType("fake_warmup_handler")

    def load(_spec: ModelSpec) -> object:
        raise AssertionError("unactivated model should not load")

    module.load = load  # type: ignore[attr-defined]
    model_registry.register(
        ModelSpec(
            name="unactivated-warmup-test",
            family="chat",
            domain="chat",
            repo="org/unactivated-warmup-test",
            module=module,
            weight_gb=1.0,
            peak_headroom_gb=1.0,
            setup_resources=(LocalPathResource(path=str(tmp_path / "missing-model")),),
        )
    )
    worker = _worker(ctx, warmup_models=["unactivated-warmup-test"])

    await worker.warmup()

    assert worker.warm is True


async def test_ttl_sweep_disabled_when_interval_zero(ctx: AppContext) -> None:
    worker = _worker(ctx, ttl_sweep_interval_s=0.0)
    worker.start()

    assert worker._ttl_task is None
    await worker.stop()


async def test_ttl_sweep_scheduled_when_interval_positive(ctx: AppContext) -> None:
    worker = _worker(ctx, ttl_sweep_interval_s=60.0)
    worker.start()

    assert worker._ttl_task is not None
    await worker.stop()
