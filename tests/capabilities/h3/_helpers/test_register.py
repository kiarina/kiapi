import pytest

from kiapi.capabilities.h3._helpers import register as register_module
from kiapi.core.capability import CapabilitySpecRegistry
from kiapi.core.model import ModelRegistry
from kiapi.core.setup import HfSnapshotResource, UrlFileResource


@pytest.fixture
def model_registry(monkeypatch: pytest.MonkeyPatch) -> ModelRegistry:
    registry = ModelRegistry()
    monkeypatch.setattr(register_module, "model_registry", registry)
    monkeypatch.setattr(
        register_module, "capability_spec_registry", CapabilitySpecRegistry()
    )
    register_module.register()
    return registry


def test_register_adds_transient_ref2va_model(model_registry: ModelRegistry) -> None:
    spec = model_registry.resolve("h3", None)

    assert spec.name == "ref2va-8bit"
    assert model_registry.resolve("h3", "minimax-h3").name == "ref2va-8bit"
    assert spec.resident is False
    assert spec.weight_gb == 0.0


def test_register_downloads_engine_pack_and_turbo_lora(
    model_registry: ModelRegistry,
) -> None:
    resources = model_registry.resolve("h3", None).setup_resources

    archive = resources[0]
    assert isinstance(archive, UrlFileResource)
    assert archive.url.endswith("/mlx-serve-bin-macos-arm64.tar.gz")
    snapshots = {r.repo: r for r in resources if isinstance(r, HfSnapshotResource)}
    assert "ddalcu/MiniMax-H3-REF2VA-MLX-Serve-8bit" in snapshots
    lora = snapshots["lightx2v/Minimax-h3-Turbo"]
    assert lora.allow_patterns == (
        "minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors",
    )
