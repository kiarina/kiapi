from collections.abc import Callable
from typing import NamedTuple


class FrameworkStrategy(NamedTuple):
    """How to measure and reclaim a framework's memory, so eviction actually
    frees it. Resolved per :class:`FrameworkName`."""

    active_bytes: Callable[[], int]
    """Current active allocation, in bytes. Deltas around load/evict give the
    measured footprint."""
    free_caches: Callable[[], None]
    """Release the framework's cached buffers after dropping refs (e.g. MLX's
    Metal buffer cache); a no-op where the runtime needs none."""
