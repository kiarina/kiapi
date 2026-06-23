"""Extract a single embedding vector from an mlx-embeddings model output."""

from typing import Any


def to_vector(output: Any) -> list[float]:
    """Extract a single embedding vector from an mlx-embeddings model output.

    mlx-embeddings returns a model-output object with ``text_embeds`` (normalized,
    pooled, shape ``(batch, dim)``). We embed one item per request, so take row 0.
    Falls back to treating the output itself as the array if there's no attribute.
    """
    import mlx.core as mx

    embeds = getattr(output, "text_embeds", None)
    if embeds is None:
        embeds = getattr(output, "pooler_output", output)
    mx.eval(embeds)
    rows = embeds.tolist()
    return rows[0] if rows and isinstance(rows[0], list) else rows
