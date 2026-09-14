"""Resolve a :class:`FrameworkName` to its :class:`FrameworkStrategy`.

A new framework plugs in by adding a ``(active_bytes, free_caches)`` pair to
``_FRAMEWORKS`` and, if it needs extra teardown, a per-module ``release(payload)``
hook (called by the manager before dropping refs).
"""

from .._schemas.framework_strategy import FrameworkStrategy
from .._types.framework_name import FrameworkName


def _mlx_active() -> int:
    import mlx.core as mx

    return int(mx.get_active_memory())


def _mlx_free() -> None:
    import mlx.core as mx

    mx.clear_cache()


def _rss_active() -> int:
    import psutil  # type: ignore[import-untyped]

    return int(psutil.Process().memory_info().rss)


def _noop_free() -> None:
    pass


_FRAMEWORKS: dict[FrameworkName, FrameworkStrategy] = {
    "mlx": FrameworkStrategy(_mlx_active, _mlx_free),
    # framework-agnostic fallback (e.g. torch/MPS until a dedicated entry lands)
    "rss": FrameworkStrategy(_rss_active, _noop_free),
}


def resolve_framework_strategy(framework: FrameworkName) -> FrameworkStrategy:
    return _FRAMEWORKS.get(framework, _FRAMEWORKS["rss"])
