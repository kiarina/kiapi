import pytest

from kiapi.capabilities.ltx2._helpers import register as register_module
from kiapi.core.capability import CapabilitySpecRegistry
from kiapi.core.model import ModelRegistry
from kiapi.core.setup import HfSnapshotResource, PythonPackageResource


def test_register_adds_mlx_video_python_package_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_registry = ModelRegistry()
    capability_registry = CapabilitySpecRegistry()
    monkeypatch.setattr(register_module, "model_registry", model_registry)
    monkeypatch.setattr(
        register_module, "capability_spec_registry", capability_registry
    )

    register_module.register()

    spec = model_registry.resolve("ltx2", "distilled")
    resources = spec.setup_resources

    assert isinstance(resources[0], PythonPackageResource)
    assert resources[0].package == "mlx-video"
    assert "github.com/Blaizzy/mlx-video.git" in resources[0].spec
    assert resources[0].import_name == "mlx_video.models.ltx_2.generate"
    assert resources[0].verify_attrs == ("PipelineType", "generate_video")
    assert resources[0].label == "mlx-video-ltx2"
    assert any(isinstance(resource, HfSnapshotResource) for resource in resources)
