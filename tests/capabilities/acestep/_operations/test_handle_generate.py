from types import SimpleNamespace
from typing import Any

from kiapi.capabilities.acestep import GenerateRequest, handle_generate


class _MemoryManager:
    def acquire(self, spec: Any) -> str:
        return "engine"


class _Module:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_track(
        self,
        engine: Any,
        params: Any,
        files: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "engine": engine,
                "params": params,
                "files": files,
            }
        )
        return {"file_id": "file_123", "task": params.task}


def test_handle_generate_uses_text2music_task(monkeypatch: Any) -> None:
    module = _Module()
    spec = SimpleNamespace(module=module, name="xl-base")

    monkeypatch.setattr(
        "kiapi.capabilities.acestep._operations.resolve_engine.model_registry.resolve",
        lambda family, model: spec,
    )
    ctx = SimpleNamespace(
        memory_manager=_MemoryManager(),
        file_store=object(),
        ensure_model_ready=lambda _spec: None,
    )
    req = GenerateRequest(prompt="bright pop", lyrics="[Instrumental]", duration=12)

    result, artifacts = handle_generate(ctx, req)  # type: ignore[arg-type]

    assert result["file_id"] == "file_123"
    assert artifacts == ["file_123"]
    assert module.calls[0]["params"].task == "text2music"
    assert module.calls[0]["params"].meta_extra() == {"model": "xl-base"}
