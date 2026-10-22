import copy
from typing import Any

import mlx.core as mx


def _copy_state(value: Any) -> Any:
    if isinstance(value, mx.array):
        return mx.array(value)
    if isinstance(value, list):
        return [_copy_state(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_copy_state(v) for v in value)
    if isinstance(value, dict):
        return {k: _copy_state(v) for k, v in value.items()}
    if hasattr(value, "state"):
        cloned = copy.copy(value)
        cloned.state = _copy_state(value.state)
        return cloned
    return copy.copy(value)
