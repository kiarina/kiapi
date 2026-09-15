import pytest

from kiapi.capabilities.ltx2._helpers import register as register_module
from kiapi.core.capability import CapabilitySpecRegistry
from kiapi.core.model import ModelRegistry
from kiapi.core.setup import HfSnapshotResource, PythonPackageResource


@pytest.fixture
def model_registry(monkeypatch: pytest.MonkeyPatch) -> ModelRegistry:
    registry = ModelRegistry()
    monkeypatch.setattr(register_module, "model_registry", registry)
    monkeypatch.setattr(
        register_module, "capability_spec_registry", CapabilitySpecRegistry()
    )
    register_module.register()
    return registry


def test_register_defaults_to_ltx25(model_registry: ModelRegistry) -> None:
    assert model_registry.default_name("ltx2") == "ltx-2.5-distilled"
    assert model_registry.resolve("ltx2", "distilled").repo == (
        "prince-canuma/LTX-2-distilled"
    )


@pytest.mark.parametrize("variant", ["ltx-2.5-distilled", "distilled"])
def test_register_adds_mlx_video_python_package_resource(
    model_registry: ModelRegistry, variant: str
) -> None:
    resources = model_registry.resolve("ltx2", variant).setup_resources

    assert isinstance(resources[0], PythonPackageResource)
    assert resources[0].package == "mlx-video"
    assert "github.com/kiarina/mlx-video.git@" in resources[0].spec
    assert resources[0].import_name == "mlx_video.models.ltx_2.generate"
    assert "LTX25_MODEL_REPO" in resources[0].verify_attrs
    assert resources[0].label == "mlx-video-ltx2"
    assert any(isinstance(resource, HfSnapshotResource) for resource in resources)


def test_register_limits_ltx25_download_to_loaded_files(
    model_registry: ModelRegistry,
) -> None:
    resources = model_registry.resolve("ltx2", "ltx-2.5-distilled").setup_resources
    snapshots = {
        resource.repo: resource
        for resource in resources
        if isinstance(resource, HfSnapshotResource)
    }

    patterns = snapshots["Lightricks/LTX-2.5"].allow_patterns or ()
    assert len(patterns) == 7
    assert all(pattern.endswith(".safetensors") for pattern in patterns)
    assert "mlx-community/gemma-4-e2b-it-bf16" in snapshots
    assert "Lightricks/LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler" in snapshots
