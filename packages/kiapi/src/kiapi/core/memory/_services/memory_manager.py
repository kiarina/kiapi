"""Global, budget-bounded resident model cache shared by every capability.

This generalizes mlx-vlm-server's per-server manager to the whole of kiapi.
Because the worker is single-flight (one job at a time, see worker.py), the model
acquired for the running job is the only one that will generate next, so it is
correct to budget only *its* peak headroom. Before a model is used we ensure:

    Σ(resident weights, excluding the target)
        + target.weight + target.peak_headroom   ≤  memory_limit_gb

evicting residents until it holds. Eviction order is **(priority asc, last_used
asc)**: lower-priority models go first, and among equal priority the
least-recently-used. So a small model you want resident gets a high ``priority``
and survives even when a big model churns through.

Two concepts are kept separate:
  - **resident weights** — long-lived, reusable, evictable (tracked here),
  - **peak headroom** — transient memory the *running* job needs on top of
    weights; only one job runs at a time, so only the target's headroom matters.

Framework specifics (so eviction actually frees memory) live in
:func:`resolve_framework_strategy`:
  - MLX: dropping Python refs is not enough — the Metal allocator keeps a buffer
    cache. After deleting we ``gc.collect()`` then ``mx.clear_cache()``. Memory is
    measured via ``mx.get_active_memory`` deltas.
  - Other frameworks plug in via a new FrameworkStrategy and an optional
    per-module ``release(payload)`` hook.

All mutating methods run on the single worker thread; only ``stats()`` is read
from the event-loop thread, so a small lock guards the dict.
"""

import gc
import logging
import threading
import time
import traceback

from kiapi.core.model import ModelSpec

from .._exceptions.memory_budget_error import MemoryBudgetError
from .._operations.resolve_framework_strategy import resolve_framework_strategy
from .._schemas.memory_stats import MemoryStats
from .._schemas.resident_model import ResidentModel
from .._schemas.resident_model_stats import ResidentModelStats
from .._settings import MemorySettings
from .._types.resident_key import ResidentKey

_GB = 1024**3
logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, settings: MemorySettings) -> None:
        self._settings: MemorySettings = settings
        self._loaded: dict[ResidentKey, ResidentModel] = {}
        self._lock = threading.Lock()

    @property
    def memory_limit_gb(self) -> float:
        limit = self._settings.memory_limit_gb

        if limit is None:
            raise RuntimeError("memory_limit_gb must be resolved before use")

        return limit

    @property
    def default_ttl_s(self) -> float:
        return self._settings.default_ttl_s

    # -- TTL -------------------------------------------------------------------

    def _effective_ttl(self, spec: ModelSpec) -> float | None:
        ttl = spec.ttl_seconds

        if ttl is None:
            ttl = self.default_ttl_s
        if ttl <= 0:
            return None

        return ttl

    def sweep_expired(
        self, *, exclude_key: ResidentKey | None = None, now: float | None = None
    ) -> list[str]:
        """Runs on the worker thread — it frees framework memory, so it must not
        be called from the event loop. Returns the freed models' names."""
        now = now if now is not None else time.monotonic()
        expired: list[ResidentKey] = []
        for key, ld in list(self._loaded.items()):
            if key == exclude_key:
                continue
            ttl = self._effective_ttl(ld.spec)
            if ttl is not None and (now - ld.last_used) > ttl:
                expired.append(key)
        freed = []
        for key in expired:
            name = self._loaded[key].spec.name if key in self._loaded else key
            self._evict(key, reason="ttl")
            freed.append(name)
        return freed

    # -- public (worker thread) ------------------------------------------------

    def acquire(self, spec: ModelSpec) -> object:
        # Free any idle-expired models first (don't touch the one we're about to
        # use) so their memory is reclaimed before we budget/load.
        self.sweep_expired(exclude_key=spec.key)
        existing = self._loaded.get(spec.key)
        if existing is not None:
            # Re-check budget: another model may have loaded since, and this
            # model's generation headroom must still fit.
            self._ensure_budget(spec, existing.weight_gb)
            existing.last_used = time.monotonic()
            return existing.payload

        self._ensure_budget(spec, spec.weight_gb)  # estimate (not loaded yet)
        loaded = self._load(spec)
        with self._lock:
            self._loaded[spec.key] = loaded
        return loaded.payload

    def reserve(
        self, need_gb: float, *, exclude_key: ResidentKey | None = None
    ) -> None:
        """Make budget room for a transient job that loads/frees its own weights.

        For providers that don't keep a resident model (e.g. mlx-video's LTX-2,
        which loads and frees per call), there's nothing to ``acquire``. Instead
        the handler reserves the peak it will transiently need: we evict residents
        by (priority asc, last_used asc) until ``resident_total + need ≤ limit``.
        Single-flight guarantees nothing else runs while the job uses that room,
        and the provider frees it when done."""
        limit = self.memory_limit_gb
        if need_gb > limit:
            raise MemoryBudgetError(
                f"transient job needs ~{need_gb:.1f} GB but the budget is only {limit:.1f} GB"
            )
        while self._resident_weight_gb(exclude_key=exclude_key) + need_gb > limit:
            victim = self._victim(exclude_key=exclude_key)
            if victim is None:
                raise MemoryBudgetError(
                    f"transient job needs ~{need_gb:.1f} GB but the budget is "
                    f"{limit:.1f} GB with nothing left to evict"
                )
            self._evict(victim)

    def stats(self) -> MemoryStats:
        """Snapshot for /health (safe from the event-loop thread)."""
        now = time.monotonic()
        with self._lock:
            loaded: list[ResidentModelStats] = []
            resident_total = 0.0
            for ld in self._loaded.values():
                ttl = self._effective_ttl(ld.spec)
                idle = round(now - ld.last_used, 1)
                resident_total += ld.weight_gb
                loaded.append(
                    ResidentModelStats(
                        name=ld.spec.name,
                        family=ld.spec.family,
                        domain=ld.spec.domain,
                        repo=ld.spec.repo,
                        weight_gb=round(ld.weight_gb, 1),
                        priority=ld.spec.priority,
                        idle_s=idle,
                        ttl_s=ttl,
                        expires_in_s=round(ttl - idle, 1) if ttl is not None else None,
                    )
                )
        return MemoryStats(
            loaded=loaded,
            resident_gb=round(resident_total, 1),
            budget_gb=self.memory_limit_gb,
        )

    def shutdown(self) -> None:
        for key in list(self._loaded):
            self._evict(key)

    # -- budget / eviction -----------------------------------------------------

    def _resident_weight_gb(self, exclude_key: ResidentKey | None = None) -> float:
        return sum(
            ld.weight_gb for key, ld in self._loaded.items() if key != exclude_key
        )

    def _ensure_budget(self, spec: ModelSpec, target_weight_gb: float) -> None:
        limit = self.memory_limit_gb
        need = target_weight_gb + spec.peak_headroom_gb
        while self._resident_weight_gb(exclude_key=spec.key) + need > limit:
            victim = self._victim(exclude_key=spec.key)
            if victim is None:
                raise MemoryBudgetError(
                    f"model {spec.name!r} needs ~{need:.1f} GB but the budget is "
                    f"{limit:.1f} GB with nothing left to evict"
                )
            self._evict(victim)

    def _victim(self, *, exclude_key: ResidentKey | None) -> ResidentKey | None:
        cands = [
            (ld.spec.priority, ld.last_used, key)
            for key, ld in self._loaded.items()
            if key != exclude_key
        ]
        if not cands:
            return None
        cands.sort()  # priority asc, then last_used asc
        return cands[0][2]

    def _evict(self, key: ResidentKey, *, reason: str = "budget") -> None:
        with self._lock:
            loaded = self._loaded.pop(key, None)
        if loaded is None:
            return
        spec = loaded.spec
        strategy = resolve_framework_strategy(spec.framework)
        before = strategy.active_bytes()
        # Optional per-module cleanup (framework-specific extras) before dropping.
        release = getattr(spec.module, "release", None)
        if release is not None:
            try:
                release(loaded.payload)
            except Exception:
                traceback.print_exc()
        del loaded
        gc.collect()
        strategy.free_caches()
        freed = max(before - strategy.active_bytes(), 0) / _GB
        logger.info(
            "evicted %s (%s) [%s] - freed ~%.1f GB",
            spec.name,
            spec.key,
            reason,
            freed,
        )

    # -- loading ---------------------------------------------------------------

    def _load(self, spec: ModelSpec) -> ResidentModel:
        strategy = resolve_framework_strategy(spec.framework)
        logger.info("loading %s (%s) ...", spec.name, spec.key)
        before = strategy.active_bytes()
        payload = spec.module.load(spec)
        measured = max(strategy.active_bytes() - before, 0) / _GB
        # Reconcile estimate with reality; fall back to the estimate if the delta
        # looks bogus (e.g. weights still lazy / not yet materialized).
        weight_gb = measured if measured > 0.5 else spec.weight_gb
        logger.info(
            "loaded %s - weight ~%.1f GB (estimate %.1f, measured %.1f)",
            spec.name,
            weight_gb,
            spec.weight_gb,
            measured,
        )
        return ResidentModel(spec, payload, weight_gb, time.monotonic())
