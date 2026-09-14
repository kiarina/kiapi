"""Compatibility patch for mlx-vlm's Qwen vision towers on mlx 0.32+.

mlx-vlm 0.6.3's ``qwen3_vl`` and ``qwen3_omni_moe`` vision towers call
``mx.repeat(seq_len, grid_thw[i, 0])`` with an array ``repeats``. mlx 0.32 accepts
only ``int`` there, so every image request fails with a ``TypeError``. mlx-vlm
0.7.1 casts it with ``int(...)``; this patch does the same by giving only those
modules an ``mx`` whose ``repeat`` casts a scalar array count to ``int``. Other
users of ``mlx.core`` are unaffected. Drop this once mlx-vlm is updated.
"""

import importlib
from typing import Any

_VISION_MODULES = (
    "mlx_vlm.models.qwen3_vl.vision",
    "mlx_vlm.models.qwen3_omni_moe.vision",
)


class _IntRepeatMx:
    _kiapi_int_repeat = True

    def __init__(self, mx: Any) -> None:
        self._mx = mx

    def __getattr__(self, name: str) -> Any:
        return getattr(self._mx, name)

    def repeat(self, array: Any, repeats: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(repeats, self._mx.array) and repeats.size == 1:
            repeats = int(repeats.item())
        return self._mx.repeat(array, repeats, *args, **kwargs)


def ensure_vision_repeat_compat() -> None:
    """Patch the Qwen vision modules once, if available."""
    for name in _VISION_MODULES:
        try:
            module: Any = importlib.import_module(name)
        except Exception:
            continue
        mx = module.mx
        if getattr(mx, "_kiapi_int_repeat", False):
            continue
        module.mx = _IntRepeatMx(mx)
