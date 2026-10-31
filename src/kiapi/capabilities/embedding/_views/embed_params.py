"""The complete contract for one embedding run.

Built from settings + request by ``resolve_embed_params``; a model's ``run`` needs
nothing else (no ``req`` / ``settings``) to produce the embeddings and the response.
``model`` is the canonical model name to echo back; ``inputs`` holds one dict of raw
modality sources per item (materialized per-model via ``parse_inputs``).
"""

from typing import Any, Literal

from pydantic import BaseModel


class EmbedParams(BaseModel):
    model: str
    inputs: list[dict[str, Any]]
    max_length: int
    dimensions: int | None = None
    encoding_format: Literal["float", "base64"] = "float"
