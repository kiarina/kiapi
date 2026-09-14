"""Shape an embedding vector into the server's ``/v1/embedding`` response dict.

Identical across handlers, so it lives here and the per-model ``run()`` calls it
after computing the vector.
"""

from typing import Any


def format_response(
    *,
    model_name: str,
    embedding: list[float],
    elapsed: float,
    prompt_tokens: int = 0,
) -> dict[str, Any]:
    """Build the ``/v1/embedding`` response dict for a single embedding."""
    return {
        "model": model_name,
        "embedding": embedding,
        "dimension": len(embedding),
        "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens},
        "timings": {"total_s": round(elapsed, 3)},
    }
