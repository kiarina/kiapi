from types import ModuleType

from kiapi.core.model import ModelSpec
from kiapi.core.setup import HfSnapshotResource


def _spec(**overrides: object) -> ModelSpec:
    base: dict[str, object] = {
        "name": "turbo",
        "family": "acestep",
        "domain": "audio",
        "repo": "org/acestep-turbo",
        "module": ModuleType("fake_handler"),
        "weight_gb": 4.0,
        "peak_headroom_gb": 2.0,
    }
    base.update(overrides)
    return ModelSpec(**base)  # type: ignore[arg-type]


def test_key_is_family_and_repo() -> None:
    spec = _spec(family="acestep", repo="org/acestep-turbo")
    assert spec.key == "acestep:org/acestep-turbo"


def test_defaults() -> None:
    spec = _spec()
    assert spec.framework == "mlx"
    assert spec.priority == 0
    assert spec.aliases == ()
    assert spec.default is False
    assert spec.resident is True
    assert spec.ttl_seconds is None
    assert spec.setup_resources == ()


def test_features_reads_module_attribute() -> None:
    module = ModuleType("fake_handler")
    module.FEATURES = {"text", "image"}  # type: ignore[attr-defined]
    spec = _spec(module=module)
    assert spec.features == {"text", "image"}


def test_features_defaults_to_empty_set() -> None:
    spec = _spec(module=ModuleType("no_caps"))
    assert spec.features == set()


def test_setup_resources_defaults_can_be_overridden() -> None:
    resource = HfSnapshotResource(repo="org/model", disk_gb=1.5)
    spec = _spec(setup_resources=(resource,))
    assert spec.setup_resources == (resource,)
