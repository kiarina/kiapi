from types import ModuleType

from kiapi.api.setup._helpers.build_setup_response import build_setup_response
from kiapi.core.model import ModelSpec
from kiapi.core.setup import HfSnapshotResource, SetupResource, SetupStatus


class FakeSetupManager:
    def __init__(self, states: dict[str, SetupStatus]) -> None:
        self._states = states
        self.calls: list[str] = []

    def status(self, resource: SetupResource) -> SetupStatus:
        self.calls.append(resource.key)
        return self._states[resource.key]


def test_reports_models_resources_and_summary() -> None:
    turbo = HfSnapshotResource(repo="org/turbo", disk_gb=5.5)
    base = HfSnapshotResource(repo="org/base", disk_gb=19.0)
    manager = FakeSetupManager(
        {
            turbo.key: SetupStatus(True, "/cache/turbo"),
            base.key: SetupStatus(False, "not downloaded"),
        }
    )
    specs = [
        _spec("turbo", (turbo,), default=True),
        _spec("base", (base,)),
        _spec("remote", ()),
    ]

    response = build_setup_response(specs, manager)

    by_name = {m.name: m for m in response.data}
    assert by_name["turbo"].status == "ready"
    assert by_name["turbo"].default is True
    assert by_name["base"].status == "missing"
    assert by_name["base"].size_gb == 19.0
    assert by_name["remote"].status == "none"
    missing = by_name["base"].resources[0]
    assert missing.ready is False
    assert missing.detail == "not downloaded"
    assert missing.activate_command == "kiapi activate --repo org/base"
    assert response.summary.models_total == 3
    assert response.summary.models_ready == 2
    assert response.summary.resources_total == 2
    assert response.summary.resources_ready == 1
    assert response.summary.installed_gb == 5.5
    assert response.summary.total_gb == 24.5


def test_checks_a_shared_resource_once() -> None:
    shared = HfSnapshotResource(repo="org/shared", disk_gb=7.3)
    manager = FakeSetupManager({shared.key: SetupStatus(True, "/cache/shared")})

    response = build_setup_response(
        [_spec("3b", (shared,)), _spec("7b", (shared,))], manager
    )

    assert manager.calls == [shared.key]
    assert response.summary.resources_total == 1
    assert [m.status for m in response.data] == ["ready", "ready"]


def _spec(
    name: str, resources: tuple[SetupResource, ...], *, default: bool = False
) -> ModelSpec:
    return ModelSpec(
        name=name,
        family="zimage",
        domain="image",
        repo=f"org/{name}",
        module=ModuleType(f"test_{name}"),
        weight_gb=1.0,
        peak_headroom_gb=1.0,
        default=default,
        setup_resources=resources,
    )
