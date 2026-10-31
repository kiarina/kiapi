"""Shape embedding vectors into the OpenAI-compatible ``/v1/embeddings`` response.

Identical across handlers, so it lives here and the per-model ``run()`` calls it
after computing the vectors.
"""

from typing import Any, Literal

from .._utils.encode_vector import encode_vector
from .._utils.resize_vector import resize_vector


def format_response(
    *,
    model_name: str,
    vectors: list[list[float]],
    elapsed: float,
    prompt_tokens: int,
    dimensions: int | None = None,
    encoding_format: Literal["float", "base64"] = "float",
) -> dict[str, Any]:
    data = []
    for index, vector in enumerate(vectors):
        resized = resize_vector(vector, dimensions)
        data.append(
            {
                "object": "embedding",
                "index": index,
                "embedding": (
                    encode_vector(resized) if encoding_format == "base64" else resized
                ),
            }
        )

    return {
        "object": "list",
        "data": data,
        "model": model_name,
        "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens},
        "timings": {"total_s": round(elapsed, 3)},
    }
