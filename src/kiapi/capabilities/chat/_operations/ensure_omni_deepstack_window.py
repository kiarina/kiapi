"""Compatibility patch for Qwen3-Omni's deepstack injection under chunked prefill.

mlx-vlm 0.7.1 passes the full-prompt ``visual_pos_masks`` and
``deepstack_visual_embeds`` to every prefill chunk and to the final one-token
step. Omni's ``_deepstack_process`` then scatters at full-prompt positions into
the shorter chunk and writes past the end of the GPU buffer: a video prompt
decodes garbage or aborts the process with a Metal page fault (upstream issue
#2099). The Qwen3-VL language model already windows both inputs per chunk; this
applies the same windowing to Omni's decoder. Drop this once mlx-vlm fixes
``qwen3_omni_moe``.
"""

from typing import Any

_PATCH_FLAG = "_kiapi_deepstack_window"


def ensure_omni_deepstack_window() -> None:
    """Patch Omni's decoder once, if available."""
    try:
        from mlx_vlm.models.qwen3_omni_moe.language import (
            Qwen3VLMoEModel,
        )
    except Exception:
        return

    if getattr(Qwen3VLMoEModel, _PATCH_FLAG, False):
        return

    from mlx_vlm.models.qwen3_omni_moe import language

    # Newer upstream represents deepstack as [batch, tokens, layers, hidden]
    # and windows it in LanguageModel. The old compact-row patch must not run.
    if hasattr(language, "expand_deepstack_visual_embeds"):
        return

    original = Qwen3VLMoEModel.__call__

    def __call__(  # type: ignore
        self,
        inputs,
        inputs_embeds=None,
        mask=None,
        cache=None,
        position_ids=None,
        visual_pos_masks=None,
        deepstack_visual_embeds=None,
        **kwargs,
    ):
        if visual_pos_masks is not None and deepstack_visual_embeds is not None:
            source = inputs_embeds if inputs_embeds is not None else inputs
            visual_pos_masks, deepstack_visual_embeds = window_deepstack(
                visual_pos_masks,
                deepstack_visual_embeds,
                start=_cache_offset(cache),
                window=source.shape[1],
            )
        return original(
            self,
            inputs,
            inputs_embeds=inputs_embeds,
            mask=mask,
            cache=cache,
            position_ids=position_ids,
            visual_pos_masks=visual_pos_masks,
            deepstack_visual_embeds=deepstack_visual_embeds,
            **kwargs,
        )

    Qwen3VLMoEModel.__call__ = __call__  # type: ignore[method-assign,assignment]
    setattr(Qwen3VLMoEModel, _PATCH_FLAG, True)


def window_deepstack(
    visual_pos_masks: Any,
    deepstack_visual_embeds: Any,
    start: int | None,
    window: int,
) -> tuple[Any, Any]:
    """Return the mask and per-layer embeds for tokens ``[start, start + window)``.

    ``start`` is ``None`` for batched generation with per-row offsets; the
    embeds cannot be split per row there, so deepstack is skipped instead of
    scattering out of bounds.
    """
    mask = visual_pos_masks[..., 0] if visual_pos_masks.ndim == 3 else visual_pos_masks
    if mask.shape[-1] == window:
        return visual_pos_masks, deepstack_visual_embeds
    if start is None or mask.shape[0] != 1:
        return None, None

    window_mask = mask[:, start : start + window]
    n_window = int(window_mask.sum().item())
    if window_mask.shape[-1] != window or n_window == 0:
        return None, None

    n_before = int(mask[:, :start].sum().item())
    embeds = [e[n_before : n_before + n_window] for e in deepstack_visual_embeds]
    return window_mask, embeds


def _cache_offset(cache: Any) -> int | None:
    c0 = cache[0] if cache else None
    if c0 is None:
        return 0
    offset = getattr(c0, "_idx", None)
    if offset is None:
        offset = c0.offset
    if isinstance(offset, int):
        return offset
    if getattr(offset, "ndim", 0) > 0:
        return None
    return int(offset.item())
