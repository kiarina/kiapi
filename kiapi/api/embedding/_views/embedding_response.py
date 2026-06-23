"""``/v1/embedding`` response model.

Mirrors the dict shaped by ``capabilities/embedding/_operations/format_response``
so the response is self-describing in OpenAPI. It is an output-side projection of
the model result (not a model-coupled view), so it lives under
``api/embedding/_views``.

``EmbeddingResponse`` is the sole public element; the nested pieces are private
since nothing references them on their own.
"""

from pydantic import BaseModel, Field


class _Usage(BaseModel):
    prompt_tokens: int = Field(
        description="Tokens in the embedded input (0 when the model does not report it)."
    )
    total_tokens: int = Field(
        description="Total tokens accounted for; equals `prompt_tokens` (no generation)."
    )


class _Timings(BaseModel):
    total_s: float = Field(description="Wall-clock embedding time in seconds.")


class EmbeddingResponse(BaseModel):
    model: str = Field(description="Resolved model name that produced the vector.")
    embedding: list[float] = Field(
        description="L2-normalized, last-token-pooled embedding vector for the item."
    )
    dimension: int = Field(description="Length of `embedding` (vector dimensionality).")
    usage: _Usage = Field(description="Token accounting for the request.")
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
