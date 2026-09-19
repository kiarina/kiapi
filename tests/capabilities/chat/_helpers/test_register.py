import pytest

from kiapi.capabilities.chat._helpers import register as register_module
from kiapi.core.capability import CapabilitySpecRegistry
from kiapi.core.model import ModelRegistry


@pytest.fixture
def model_registry(monkeypatch: pytest.MonkeyPatch) -> ModelRegistry:
    registry = ModelRegistry()
    monkeypatch.setattr(register_module, "model_registry", registry)
    monkeypatch.setattr(
        register_module, "capability_spec_registry", CapabilitySpecRegistry()
    )
    register_module.register()
    return registry


@pytest.mark.parametrize("model", ["qwen3.6-27b", "qwen3.8-27b"])
def test_text_models_reserve_apc_and_generation_memory(
    model_registry: ModelRegistry, model: str
) -> None:
    spec = model_registry.resolve("chat", model)

    assert spec.peak_headroom_gb == 20.0
