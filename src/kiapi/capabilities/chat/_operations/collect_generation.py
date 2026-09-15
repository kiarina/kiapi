"""Collect a non-streaming completion from ``stream_generate`` chunks.

Non-streaming runs use the same chunk stream as streaming ones instead of
mlx-vlm's ``generate`` so ``limit_to_context`` applies to both. Mirrors
``generate``: join the chunk text, then apply the processor's ``clean_output``.
Returns (text, last_chunk); the last chunk carries the token counts and
``finish_reason``.
"""

from collections.abc import Iterable


def collect_generation(processor, chunks: Iterable) -> tuple[str, object | None]:  # type: ignore
    text = ""
    last = None
    for chunk in chunks:
        text += str(getattr(chunk, "text", "") or "")
        last = chunk

    clean_output = getattr(processor, "clean_output", None)
    if callable(clean_output):
        text = clean_output(text)
    return text, last
