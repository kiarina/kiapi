import time
from typing import Any


def select_live_node(
    entries: Any,
    ttl_s: float,
    *,
    now: float | None = None,
) -> str | None:
    """Return the node ID with the most recent heartbeat within ``ttl_s``.

    ``entries`` maps a node ID to a liveness record holding a ``ts`` timestamp
    (epoch seconds). Stale or malformed records are ignored. Returns ``None``
    when no node has reported within the staleness window.
    """
    if not isinstance(entries, dict):
        return None

    reference = time.time() if now is None else now
    best_node: str | None = None
    best_ts = float("-inf")

    for node_id, record in entries.items():
        if not isinstance(record, dict):
            continue
        ts = record.get("ts")
        if not isinstance(ts, (int, float)) or isinstance(ts, bool):
            continue
        if reference - ts > ttl_s:
            continue
        if ts > best_ts:
            best_ts = ts
            best_node = node_id

    return best_node
