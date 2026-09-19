import sys
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from kiapi.capabilities.chat._operations.ensure_omni_apc_embeddings import (
    ensure_omni_apc_embeddings,
)


def test_omni_restored_suffix_skips_media_and_preserves_full_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = Mock(return_value="cold embeddings")
    model_cls: Any = type("Model", (), {"get_input_embeddings": original})
    apc = SimpleNamespace(
        multimodal_token_ids_from_config=lambda c: (
            {c.image_token_id, c.video_token_id}
            if hasattr(c, "image_token_id")
            else set()
        )
    )
    modules: dict[str, dict[str, Any]] = {
        "mlx_vlm": {"apc": apc},
        "mlx_vlm.models.base": {"InputEmbeddingsFeatures": SimpleNamespace},
        "mlx_vlm.models.qwen3_omni_moe.qwen3_omni_moe": {"Model": model_cls},
    }
    for name, attrs in modules.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    ensure_omni_apc_embeddings()
    wrapped = model_cls.get_input_embeddings
    ensure_omni_apc_embeddings()
    assert wrapped is model_cls.get_input_embeddings
    model: Any = model_cls()
    model.language_model = SimpleNamespace(
        model=SimpleNamespace(embed_tokens=lambda x: "text embeddings")
    )
    suffix = SimpleNamespace(shape=(1, 2))
    positions = SimpleNamespace(shape=(3, 1, 200))
    delta = object()
    result = model.get_input_embeddings(
        suffix,
        position_ids=positions,
        rope_deltas=delta,
        input_features=object(),
        pixel_values_videos=object(),
    )
    assert result.inputs_embeds == "text embeddings"
    assert result.position_ids is positions
    assert result.rope_deltas is delta
    original.assert_not_called()
    assert model.get_input_embeddings(suffix) == "cold embeddings"
    assert (
        model.get_input_embeddings(suffix, position_ids=SimpleNamespace(shape=(1, 2)))
        == "cold embeddings"
    )
    config = SimpleNamespace(
        model_type="qwen3_omni_moe",
        thinker_config=SimpleNamespace(
            image_token_id=11, video_token_id=12, audio_token_id=13
        ),
    )
    assert apc.multimodal_token_ids_from_config(config) == {11, 12, 13}
