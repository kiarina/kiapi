from types import SimpleNamespace

import pytest

from kiapi.capabilities.chat._helpers import register as register_module
from kiapi.core.capability import CapabilitySpecRegistry
from kiapi.core.model import ModelRegistry


@pytest.mark.parametrize("model", ["qwen3-omni", "qwen3.8-27b", "qwen3.8-flash-next"])
@pytest.mark.parametrize(
    "enabled,cap,expected", [(True, 16.0, 20.0), (True, 2.5, 6.5), (False, 16.0, 4.0)]
)
def test_chat_models_reserve_configured_apc_and_generation_memory(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
    enabled: bool,
    cap: float,
    expected: float,
) -> None:
    registry = ModelRegistry()
    monkeypatch.setattr(register_module, "model_registry", registry)
    monkeypatch.setattr(
        register_module, "capability_spec_registry", CapabilitySpecRegistry()
    )
    monkeypatch.setattr(
        register_module.settings_manager,
        "get_settings",
        lambda: SimpleNamespace(apc_enabled=enabled, apc_memory_max_gb=cap),
    )
    register_module.register()
    assert registry.resolve("chat", model).peak_headroom_gb == expected
