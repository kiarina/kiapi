"""``/v1/embeddings`` response model.

Mirrors the dict shaped by ``capabilities/embedding/_operations/format_response``
so the response is self-describing in OpenAPI. It is an output-side projection of
the model result (not a model-coupled view), so it lives under
``api/embedding/_views``.

``EmbeddingResponse`` is the sole public element; the nested pieces are private
since nothing references them on their own.
"""

from typing import Literal

from pydantic import BaseModel, Field


class _Embedding(BaseModel):
    object: Literal["embedding"] = Field(description="Always `embedding`.")
    index: int = Field(description="Position of the input in the request.")
    embedding: list[float] | str = Field(
        description=(
            "L2-normalized, last-token-pooled vector: a number array, or base64 "
            "when `encoding_format` is `base64`."
        )
    )


class _Usage(BaseModel):
    prompt_tokens: int = Field(
        description="Text tokens in the inputs. Images are not counted."
    )
    total_tokens: int = Field(
        description="Total tokens accounted for; equals `prompt_tokens` (no generation)."
    )


class _Timings(BaseModel):
    total_s: float = Field(description="Wall-clock embedding time in seconds.")


class EmbeddingResponse(BaseModel):
    object: Literal["list"] = Field(description="Always `list`.")
    data: list[_Embedding] = Field(description="One embedding per input, in order.")
    model: str = Field(description="Resolved model name that produced the vectors.")
    usage: _Usage = Field(description="Token accounting for the request.")
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
