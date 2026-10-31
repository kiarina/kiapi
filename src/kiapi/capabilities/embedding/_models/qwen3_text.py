"""Handler for Qwen3-Embedding-8B (text embeddings; ``model_type: qwen3``).

A text-only embedding model. Owns its own load + embed flow; shares the
input-parsing and response-shaping operations with the VL handler.
"""

import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from kiapi.core.model import ModelSpec

from .._operations.format_response import format_response
from .._operations.parse_inputs import parse_inputs
from .._utils.ensure_token_limit import ensure_token_limit
from .._utils.to_vector import to_vector
from .._views.embed_params import EmbedParams

FEATURES = {"text"}
DIMENSION_RANGE = (32, 4096)


def load(spec: ModelSpec) -> SimpleNamespace:
    from mlx_embeddings import load as _load  # type: ignore

    model, processor = _load(spec.repo)
    return SimpleNamespace(model=model, processor=processor)


def warmup(payload: SimpleNamespace) -> None:
    run(
        payload,
        EmbedParams(
            model="qwen3-embedding-8b", inputs=[{"text": "hi"}], max_length=512
        ),
    )


def run(payload: SimpleNamespace, params: EmbedParams) -> dict[str, Any]:
    from mlx_embeddings import generate

    model, processor = payload.model, payload.processor
    # text-only: parse_inputs validates capabilities; no media files are written,
    # so the tmp_dir is never actually touched.
    tmp_dir = Path(tempfile.gettempdir())
    texts = [
        parse_inputs(item, tmp_dir, allow=FEATURES)["text"] for item in params.inputs
    ]
    token_counts = [len(processor.encode(text)) for text in texts]
    for token_count in token_counts:
        ensure_token_limit(token_count, params.max_length)

    t0 = time.time()
    # mlx_embeddings.generate ignores max_length for a str input. Items run one at
    # a time because a padded batch costs the longest item's length for every item.
    vectors = [to_vector(generate(model, processor, text)) for text in texts]
    elapsed = time.time() - t0

    return format_response(
        model_name=params.model,
        vectors=vectors,
        elapsed=elapsed,
        prompt_tokens=sum(token_counts),
        dimensions=params.dimensions,
        encoding_format=params.encoding_format,
    )
