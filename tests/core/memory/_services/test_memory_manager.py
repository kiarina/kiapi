"""MemoryManager budget/eviction/TTL logic, exercised CPU-only.

The fake handler module's ``load()`` allocates nothing, so the manager's measured
footprint stays below its 0.5 GB reconciliation floor and ``weight_gb`` falls back
to the spec estimate — making budgets deterministic. Specs use the framework-
agnostic ``"rss"`` strategy (psutil), so no MLX/GPU is touched.
"""

from types import ModuleType

import pytest

from kiapi.core.memory import MemoryBudgetError, MemoryManager, MemorySettings
from kiapi.core.model import ModelSpec


def _module(*, release_log: list[object] | None = None) -> ModuleType:
    mod = ModuleType("fake_handler")

    def load(spec: ModelSpec) -> object:
        return {"payload_for": spec.name}

    mod.load = load  # type: ignore[attr-defined]
    if release_log is not None:

        def release(payload: object) -> None:
            release_log.append(payload)

        mod.release = release  # type: ignore[attr-defined]
    return mod


def _spec(
    name: str,
    *,
    weight_gb: float = 1.0,
    peak_headroom_gb: float = 1.0,
    priority: int = 0,
    ttl_seconds: float | None = None,
    module: ModuleType | None = None,
) -> ModelSpec:
    return ModelSpec(
        name=name,
        family="acestep",
        domain="audio",
        repo=f"org/acestep-{name}",
        module=module or _module(),
        weight_gb=weight_gb,
        peak_headroom_gb=peak_headroom_gb,
        framework="rss",
        priority=priority,
        ttl_seconds=ttl_seconds,
    )


def _manager(limit_gb: float = 100.0, default_ttl_s: float = 1800.0) -> MemoryManager:
    return MemoryManager(
        MemorySettings(memory_limit_gb=limit_gb, default_ttl_s=default_ttl_s)
    )


def _resident_names(mgr: MemoryManager) -> set[str]:
    return {ld.name for ld in mgr.stats().loaded}


# -- properties ---------------------------------------------------------------


def test_settings_properties() -> None:
    mgr = _manager(limit_gb=42.0, default_ttl_s=600.0)
    assert mgr.memory_limit_gb == 42.0
    assert mgr.default_ttl_s == 600.0


# -- acquire ------------------------------------------------------------------


def test_acquire_loads_and_returns_payload() -> None:
    mgr = _manager()
    spec = _spec("turbo")

    payload = mgr.acquire(spec)

    assert payload == {"payload_for": "turbo"}
    assert _resident_names(mgr) == {"turbo"}


def test_acquire_is_cached_on_second_call() -> None:
    mgr = _manager()
    spec = _spec("turbo")

    first = mgr.acquire(spec)
    second = mgr.acquire(spec)

    assert first is second
    assert len(mgr.stats().loaded) == 1


def test_acquire_model_larger_than_budget_raises() -> None:
    mgr = _manager(limit_gb=5.0)
    spec = _spec("big", weight_gb=10.0, peak_headroom_gb=2.0)

    with pytest.raises(MemoryBudgetError):
        mgr.acquire(spec)


# -- budget eviction ----------------------------------------------------------


def test_acquire_evicts_to_fit_budget() -> None:
    mgr = _manager(limit_gb=10.0)
    mgr.acquire(_spec("a", weight_gb=7.0))
    # need = 7 + 1; resident a = 7; 7 + 8 > 10 → a evicted
    mgr.acquire(_spec("b", weight_gb=7.0))

    assert _resident_names(mgr) == {"b"}


def test_eviction_prefers_lower_priority() -> None:
    mgr = _manager(limit_gb=10.0)
    mgr.acquire(_spec("keep", weight_gb=4.0, priority=10))
    mgr.acquire(_spec("drop", weight_gb=4.0, priority=0))
    # both resident (4 + 4 + 1 = 9 ≤ 10). Now a big one forces one eviction:
    # need = 4 + 1 = 5; resident 8; evict lowest priority ("drop") → 4 + 5 = 9 ≤ 10
    mgr.acquire(_spec("new", weight_gb=4.0, priority=5))

    assert _resident_names(mgr) == {"keep", "new"}


def test_eviction_breaks_priority_ties_by_lru() -> None:
    mgr = _manager(limit_gb=10.0)
    mgr.acquire(_spec("older", weight_gb=4.0))
    mgr.acquire(_spec("newer", weight_gb=4.0))
    # equal priority (0); "older" was used least recently → evicted first
    mgr.acquire(_spec("new", weight_gb=4.0))

    assert _resident_names(mgr) == {"newer", "new"}


# -- reserve ------------------------------------------------------------------


def test_reserve_evicts_until_room() -> None:
    mgr = _manager(limit_gb=10.0)
    mgr.acquire(_spec("a", weight_gb=4.0))
    mgr.acquire(_spec("b", weight_gb=4.0))

    mgr.reserve(8.0)  # resident 8 + 8 > 10 → evict both

    assert _resident_names(mgr) == set()


def test_reserve_keeps_what_fits() -> None:
    mgr = _manager(limit_gb=10.0)
    mgr.acquire(_spec("a", weight_gb=4.0))

    mgr.reserve(5.0)  # 4 + 5 ≤ 10 → keep a

    assert _resident_names(mgr) == {"a"}


def test_reserve_more_than_budget_raises() -> None:
    mgr = _manager(limit_gb=10.0)
    with pytest.raises(MemoryBudgetError):
        mgr.reserve(11.0)


def test_reserve_excludes_key_from_total_and_victims() -> None:
    mgr = _manager(limit_gb=10.0)
    a = _spec("a", weight_gb=4.0)
    mgr.acquire(a)
    mgr.acquire(_spec("b", weight_gb=4.0))
    # 'a' is excluded: it isn't counted (only b's 4 GB is) and can't be evicted.
    # need 7: 4 + 7 > 10 → evict b → 0 + 7 ≤ 10. 'a' survives.
    mgr.reserve(7.0, exclude_key=a.key)

    assert _resident_names(mgr) == {"a"}


# -- TTL sweep ----------------------------------------------------------------


def test_sweep_expired_frees_idle_models() -> None:
    mgr = _manager(default_ttl_s=100.0)
    spec = mgr_acquire(mgr, "turbo")

    # far enough in the future that the 100s TTL has lapsed
    freed = mgr.sweep_expired(now=_future(mgr, spec))

    assert freed == ["turbo"]
    assert _resident_names(mgr) == set()


def test_sweep_expired_excludes_key() -> None:
    mgr = _manager(default_ttl_s=100.0)
    spec = mgr_acquire(mgr, "turbo")

    freed = mgr.sweep_expired(exclude_key=spec.key, now=_future(mgr, spec))

    assert freed == []
    assert _resident_names(mgr) == {"turbo"}


def test_spec_ttl_zero_never_expires() -> None:
    mgr = _manager(default_ttl_s=100.0)
    spec = _spec("pinned", ttl_seconds=0.0)
    mgr.acquire(spec)

    freed = mgr.sweep_expired(now=_future(mgr, spec))

    assert freed == []
    assert _resident_names(mgr) == {"pinned"}


def test_spec_ttl_overrides_default() -> None:
    mgr = _manager(default_ttl_s=100000.0)
    spec = _spec("short", ttl_seconds=10.0)
    mgr.acquire(spec)

    # 10s spec TTL lapses even though the global default is huge
    freed = mgr.sweep_expired(now=_last_used(mgr, spec) + 11.0)

    assert freed == ["short"]


# -- stats / shutdown / release ----------------------------------------------


def test_stats_shape() -> None:
    mgr = _manager(limit_gb=50.0, default_ttl_s=100.0)
    mgr.acquire(_spec("turbo", weight_gb=4.0, priority=3))

    stats = mgr.stats()

    assert stats.budget_gb == 50.0
    assert stats.resident_gb == 4.0
    [entry] = stats.loaded
    assert entry.name == "turbo"
    assert entry.family == "acestep"
    assert entry.domain == "audio"
    assert entry.weight_gb == 4.0
    assert entry.priority == 3
    assert entry.ttl_s == 100.0
    assert entry.idle_s >= 0.0


def test_shutdown_evicts_everything() -> None:
    mgr = _manager()
    mgr.acquire(_spec("a"))
    mgr.acquire(_spec("b"))

    mgr.shutdown()

    assert _resident_names(mgr) == set()


def test_release_hook_called_on_eviction() -> None:
    mgr = _manager(limit_gb=10.0)
    log: list[object] = []
    a = _spec("a", weight_gb=7.0, module=_module(release_log=log))
    mgr.acquire(a)
    mgr.acquire(_spec("b", weight_gb=7.0))  # forces eviction of a

    assert log == [{"payload_for": "a"}]


# -- helpers reaching into resident bookkeeping -------------------------------


def mgr_acquire(mgr: MemoryManager, name: str) -> ModelSpec:
    spec = _spec(name)
    mgr.acquire(spec)
    return spec


def _last_used(mgr: MemoryManager, spec: ModelSpec) -> float:
    return mgr._loaded[spec.key].last_used


def _future(mgr: MemoryManager, spec: ModelSpec) -> float:
    return _last_used(mgr, spec) + 10_000.0
