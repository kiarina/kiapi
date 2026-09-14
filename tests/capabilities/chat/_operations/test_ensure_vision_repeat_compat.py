import pytest

from kiapi.capabilities.chat._operations.ensure_vision_repeat_compat import (
    ensure_vision_repeat_compat,
)


def test_vision_mx_repeat_accepts_scalar_array_count():  # type: ignore
    mx = pytest.importorskip("mlx.core")
    vision = pytest.importorskip("mlx_vlm.models.qwen3_vl.vision")

    ensure_vision_repeat_compat()
    ensure_vision_repeat_compat()

    out = vision.mx.repeat(mx.array(5), mx.array(3), stream=mx.cpu)

    assert out.tolist() == [5, 5, 5]
    assert vision.mx.array is mx.array
    assert not hasattr(mx, "_kiapi_int_repeat")
