import pytest

from kiapi.capabilities.chat._operations.ensure_omni_deepstack_window import (
    window_deepstack,
)

mx = pytest.importorskip("mlx.core")


def _inputs():  # type: ignore
    # 10-token prompt; visual tokens at positions 2..7 (rows 0..5 of the embeds).
    mask = mx.array([[0, 0, 1, 1, 1, 1, 1, 1, 0, 0]], dtype=mx.bool_)
    embeds = [mx.arange(6) * 10, mx.arange(6) * 100]
    return mask, embeds


def test_window_slices_mask_and_embeds_for_a_middle_chunk():  # type: ignore
    with mx.stream(mx.cpu):
        mask, embeds = _inputs()
        out_mask, out_embeds = window_deepstack(mask, embeds, start=4, window=4)

        assert out_mask.tolist() == [[True, True, True, True]]
        assert [e.tolist() for e in out_embeds] == [
            [20, 30, 40, 50],
            [200, 300, 400, 500],
        ]


def test_window_without_visual_tokens_skips_deepstack():  # type: ignore
    with mx.stream(mx.cpu):
        mask, embeds = _inputs()

        assert window_deepstack(mask, embeds, start=0, window=2) == (None, None)
        assert window_deepstack(mask, embeds, start=9, window=1) == (None, None)


def test_decode_step_past_the_prompt_skips_deepstack():  # type: ignore
    with mx.stream(mx.cpu):
        mask, embeds = _inputs()

        assert window_deepstack(mask, embeds, start=12, window=1) == (None, None)


def test_aligned_mask_is_passed_through():  # type: ignore
    with mx.stream(mx.cpu):
        mask, embeds = _inputs()
        out_mask, out_embeds = window_deepstack(mask, embeds, start=0, window=10)

        assert out_mask is mask
        assert out_embeds is embeds


def test_batched_offsets_skip_deepstack():  # type: ignore
    with mx.stream(mx.cpu):
        mask, embeds = _inputs()

        assert window_deepstack(mask, embeds, start=None, window=4) == (None, None)
