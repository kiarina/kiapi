"""The single-flight worker — kiapi's one hard rule: only one job runs at a time.

All heavy work (model load, eviction, warmup, every generation, across every
capability) runs on ONE dedicated thread (``ThreadPoolExecutor(max_workers=1)``).
This is required for MLX correctness (arrays/streams are thread-affine) AND it is
what makes the global memory budget sound: the model being acquired for the
running job is the only one generating, so budgeting just its peak headroom is
correct (see core/memory). Concurrent HTTP requests are accepted and simply queue.

If you need real parallelism, run multiple kiapi processes, each scoped to a
subset of capabilities with its own slice of the memory budget.

A job's work is supplied as a JobThunk. The worker drives the job's lifecycle
(running → succeeded/failed) and resolves the caller's future. Sync callers await
the future (with a timeout); async callers drop it and poll the job store.
"""

import asyncio
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

from kiapi.core.app import AppContext
from kiapi.core.job import Job, ProgressReporter
from kiapi.core.model import ModelKey
from kiapi.core.setup import SetupRequiredError

from .._settings import WorkerSettings
from .._types.job_thunk import JobThunk

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        settings: WorkerSettings,
        ctx: AppContext,
    ) -> None:
        self.settings: WorkerSettings = settings
        self.ctx: AppContext = ctx
        self.queue: asyncio.Queue[tuple[Job, JobThunk, asyncio.Future]] = (
            asyncio.Queue()
        )
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kiapi")
        self.warm = False
        self._task: asyncio.Task | None = None
        self._ttl_task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="kiapi-worker")
        if self.settings.ttl_sweep_interval_s > 0:
            self._ttl_task = asyncio.create_task(
                self._ttl_loop(), name="kiapi-ttl-sweep"
            )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
        if self._ttl_task is not None:
            self._ttl_task.cancel()
        # Free resident models on the worker thread, then tear it down.
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, self.ctx.memory_manager.shutdown)
        except Exception:
            traceback.print_exc()
        self.executor.shutdown(wait=False, cancel_futures=True)

    async def submit(self, job: Job, fn: JobThunk) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        await self.queue.put((job, fn, fut))
        return fut

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            job, fn, fut = await self.queue.get()
            job.mark_running()
            # Bind a reporter for this job so capability code can push coarse
            # progress via ProgressReporter.current(); run_bound installs it on
            # the worker thread, where the thunk actually executes.
            reporter = ProgressReporter(job)
            try:
                result, artifacts = await loop.run_in_executor(
                    self.executor, reporter.run_bound, fn
                )
                job.mark_succeeded(result, artifacts)
                if not fut.done():
                    fut.set_result(result)
            except Exception as exc:
                traceback.print_exc()
                job.mark_failed(str(exc))
                if not fut.done():
                    fut.set_exception(exc)

    async def _ttl_loop(self) -> None:
        """The sweep runs on the worker thread (shared executor), so it serializes
        with generations and respects MLX thread-affinity — it frees models past
        their TTL even when no requests arrive."""
        loop = asyncio.get_running_loop()
        interval = self.settings.ttl_sweep_interval_s
        while True:
            await asyncio.sleep(interval)
            try:
                freed = await loop.run_in_executor(
                    self.executor, self.ctx.memory_manager.sweep_expired
                )
                if freed:
                    logger.info("idle sweep freed: %s", freed)
            except Exception:
                traceback.print_exc()

    async def warmup(self) -> None:
        """Each model is loaded + primed on the worker thread; acquire evicts as
        needed to respect the memory budget."""
        model_names = self.settings.warmup_models
        if not model_names:
            self.warm = True
            return
        loop = asyncio.get_running_loop()
        for name in model_names:
            try:
                await loop.run_in_executor(self.executor, self._warm_one, name)
            except Exception:
                traceback.print_exc()
        self.warm = True

    def _warm_one(self, name: ModelKey) -> None:
        """Runs on the worker thread."""
        from kiapi.core.model import model_registry

        # A warmup name is a model name; find which family owns it.
        spec = None
        for family in model_registry.families():
            try:
                spec = model_registry.resolve(family, name)
                break
            except Exception:
                continue
        if spec is None:
            logger.warning("unknown warmup model %r; skipping", name)
            return
        if not spec.resident:
            # Transient providers (e.g. video) load/free per call — nothing to
            # keep resident. Prime via the module's own warmup if it has one.
            warm = getattr(spec.module, "warmup", None)
            if warm is not None:
                try:
                    self.ctx.ensure_model_ready(spec)
                except SetupRequiredError as exc:
                    logger.warning("skipping warmup for %s: %s", spec.name, exc)
                    return
                warm(None)
            return
        try:
            self.ctx.ensure_model_ready(spec)
        except SetupRequiredError as exc:
            logger.warning("skipping warmup for %s: %s", spec.name, exc)
            return
        payload = self.ctx.memory_manager.acquire(spec)
        warm = getattr(spec.module, "warmup", None)
        if warm is not None:
            warm(payload)
