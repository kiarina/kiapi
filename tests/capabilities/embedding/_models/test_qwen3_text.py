import sys
from types import SimpleNamespace
from typing import Any

import pytest

from kiapi.capabilities import CapabilityError
from kiapi.capabilities.embedding._models import qwen3_text
from kiapi.capabilities.embedding._views.embed_params import EmbedParams


class _Processor:
    def encode(self, text: str) -> list[int]:
        return [0] * len(text)


def _install_generate(monkeypatch: pytest.MonkeyPatch, calls: list[Any]) -> None:
    def generate(model: Any, processor: Any, text: str) -> Any:
        calls.append(text)
        return SimpleNamespace(text_embeds=[[1.0, 0.0]])

    monkeypatch.setitem(
        sys.modules, "mlx_embeddings", SimpleNamespace(generate=generate)
    )
    monkeypatch.setattr(qwen3_text, "to_vector", lambda output: output.text_embeds[0])


def test_run_embeds_each_item_and_counts_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _install_generate(monkeypatch, calls)
    payload = SimpleNamespace(model=object(), processor=_Processor())
    params = EmbedParams(
        model="m", inputs=[{"text": "ab"}, {"text": "cde"}], max_length=3
    )

    result = qwen3_text.run(payload, params)

    assert calls == ["ab", "cde"]
    assert [item["index"] for item in result["data"]] == [0, 1]
    assert result["usage"]["prompt_tokens"] == 5


def test_run_rejects_long_text_before_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _install_generate(monkeypatch, calls)
    payload = SimpleNamespace(model=object(), processor=_Processor())
    params = EmbedParams(
        model="m", inputs=[{"text": "ab"}, {"text": "cdef"}], max_length=3
    )

    with pytest.raises(CapabilityError, match="4 tokens"):
        qwen3_text.run(payload, params)

    assert calls == []
