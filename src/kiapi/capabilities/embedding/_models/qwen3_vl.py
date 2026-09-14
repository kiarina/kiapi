"""Handler for Qwen3-VL-Embedding-2B (text + image embeddings; ``model_type: qwen3_vl``).

Owns the full embed flow for the multimodal embedding model. The MLX-converted
processor may be missing the ``chat_template`` and token-id attributes that
Transformers normally sets up, so :func:`load` patches them in after loading (a
known Qwen3-VL quirk, carried over from the original single-purpose server).

Embedding is done via the model's high-level ``process([item], processor=...)``
API, where ``item`` is ``{"text": ..., "image": <path>}`` (either key optional).
"""

import shutil
import time
from types import SimpleNamespace
from typing import Any

from kiapi.core.model import ModelSpec
from kiapi.core.workdir import create_work_dir

from .._operations.format_response import format_response
from .._operations.parse_inputs import parse_inputs
from .._utils.to_vector import to_vector
from .._views.embed_params import EmbedParams

FEATURES = {"text", "image"}

# Source repo for the chat template, when the converted processor lacks one.
TEMPLATE_SOURCE_MODEL_ID = "Qwen/Qwen3-VL-Embedding-2B"


def load(spec: ModelSpec) -> SimpleNamespace:
    from mlx_embeddings import load as _load  # type: ignore

    model, processor = _load(spec.repo)
    payload = SimpleNamespace(model=model, processor=processor)
    _patch_processor(payload.processor)
    return payload


def warmup(payload: SimpleNamespace) -> None:
    run(
        payload,
        EmbedParams(
            model="qwen3-vl-embedding-2b", inputs={"text": "hi"}, max_length=512
        ),
    )


def _patch_processor(processor: Any) -> None:
    """Patch in the chat template / token-id attributes the converted processor
    may be missing (Qwen3-VL quirk). Best-effort and idempotent."""
    inner = getattr(processor, "processor", None)
    tokenizer = getattr(processor, "tokenizer", None)

    if getattr(processor, "chat_template", None) is None:
        try:
            chat_template = processor._load_chat_template(TEMPLATE_SOURCE_MODEL_ID)
            if inner is not None:
                inner.chat_template = chat_template
            if tokenizer is not None:
                tokenizer.chat_template = chat_template
        except Exception:
            pass

    if inner is not None:
        image_token_id = getattr(processor, "image_token_id", None)
        video_token_id = getattr(processor, "video_token_id", None)
        if image_token_id is not None:
            inner.image_ids = [image_token_id]
        if video_token_id is not None:
            inner.video_ids = [video_token_id]
        inner.audio_ids = []


def run(payload: SimpleNamespace, params: EmbedParams) -> dict[str, Any]:
    model, processor = payload.model, payload.processor
    tmp_dir = create_work_dir("embedding/qwen3_vl")
    try:
        parsed = parse_inputs(params.inputs, tmp_dir, allow=FEATURES)

        item: dict[str, Any] = {}
        if "text" in parsed:
            item["text"] = parsed["text"]
        if "image" in parsed:
            item["image"] = parsed["image"]  # local file path

        t0 = time.time()
        embeddings = model.process([item], processor=processor)
        elapsed = time.time() - t0

        return format_response(
            model_name=params.model,
            embedding=to_vector(embeddings),
            elapsed=elapsed,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
