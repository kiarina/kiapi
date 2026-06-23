"""The complete contract for one embedding run.

Built from settings + request by ``resolve_embed_params``; a model's ``run`` needs
nothing else (no ``req`` / ``settings``) to produce the embedding and its response.
``model`` is the canonical model name to echo back; ``inputs`` are the request's
raw modality sources (materialized per-model via ``parse_inputs``).
"""

from typing import Any

from pydantic import BaseModel


class EmbedParams(BaseModel):
    model: str
    inputs: dict[str, Any]
    max_length: int
