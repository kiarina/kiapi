"""Stop generation once the prompt plus generated tokens fill the context window.

mlx-vlm only bounds generation by ``max_tokens``. The prompt length (image and
video tokens included) is known only after prefill, and mlx-vlm reports it on
every chunk, so the context bound is enforced here. On the cut this yields a
final empty chunk with ``finish_reason="length"``, the same shape mlx-vlm yields
when ``max_tokens`` runs out.
"""

from collections.abc import Iterable, Iterator
from copy import copy


def limit_to_context(chunks: Iterable, context_window: int | None) -> Iterator:
    for chunk in chunks:
        yield chunk
        if context_window is None or getattr(chunk, "finish_reason", None):
            continue
        used = getattr(chunk, "prompt_tokens", 0) + getattr(
            chunk, "generation_tokens", 0
        )
        if used >= context_window:
            final = copy(chunk)
            final.text = ""
            final.finish_reason = "length"
            yield final
            close = getattr(chunks, "close", None)
            if callable(close):
                close()
            return
