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
from .._utils.to_vector import to_vector
from .._views.embed_params import EmbedParams

FEATURES = {"text"}


def load(spec: ModelSpec) -> SimpleNamespace:
    from mlx_embeddings import load as _load  # type: ignore

    model, processor = _load(spec.repo)
    return SimpleNamespace(model=model, processor=processor)


def warmup(payload: SimpleNamespace) -> None:
    run(
        payload,
        EmbedParams(model="qwen3-embedding-8b", inputs={"text": "hi"}, max_length=512),
    )


def run(payload: SimpleNamespace, params: EmbedParams) -> dict[str, Any]:
    from mlx_embeddings import generate

    model, processor = payload.model, payload.processor
    # text-only: parse_inputs validates capabilities; no media files are written,
    # so the tmp_dir is never actually touched.
    parsed = parse_inputs(params.inputs, Path(tempfile.gettempdir()), allow=FEATURES)

    t0 = time.time()
    output = generate(model, processor, parsed["text"], max_length=params.max_length)
    elapsed = time.time() - t0

    return format_response(
        model_name=params.model,
        embedding=to_vector(output),
        elapsed=elapsed,
    )
