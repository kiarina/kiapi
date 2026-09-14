from types import ModuleType

import pytest
from click.testing import CliRunner

from kiapi.cli.status import cli as status_cli
from kiapi.core.model import ModelSpec
from kiapi.core.setup import HfSnapshotResource, SetupResource, SetupStatus


class FakeSetupManager:
    def __init__(self, states: dict[str, SetupStatus]) -> None:
        self._states = states

    def status(self, resource: SetupResource) -> SetupStatus:
        return self._states[resource.key]


def test_status_shows_summary_table_without_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = HfSnapshotResource(repo="org/model", disk_gb=3.5)
    specs = [
        _spec(
            name="base",
            repo="org/model",
            resources=(resource,),
            default=True,
        )
    ]
    manager = FakeSetupManager({resource.key: SetupStatus(True, "/cache/org/model")})
    _patch_status_inputs(monkeypatch, specs, manager)

    result = CliRunner().invoke(status_cli.status, [])

    assert result.exit_code == 0
    assert "kiapi setup status" in result.output
    assert "Models:    1 ready / 1 total" in result.output
    assert "Resources: 1 ready / 1 total" in result.output
    assert "Domain  Family  Model" in result.output
    assert "image   zimage  base *" in result.output
    assert "ready" in result.output
    assert "1/1" in result.output
    assert "~3.5 GB" in result.output
    assert "Size:      ~3.5 GB installed / ~3.5 GB total" in result.output
    assert "All resources are ready." in result.output
    assert "repository:" not in result.output
    assert "/cache/org/model" not in result.output


def test_status_verbose_shows_repository_and_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = HfSnapshotResource(repo="org/model", disk_gb=3.5)
    specs = [_spec(name="base", repo="logical-model", resources=(resource,))]
    manager = FakeSetupManager({resource.key: SetupStatus(True, "/cache/org/model")})
    _patch_status_inputs(monkeypatch, specs, manager)

    result = CliRunner().invoke(status_cli.status, ["--verbose"])

    assert result.exit_code == 0
    assert "repository: logical-model" in result.output
    assert "ready   hf_snapshot" in result.output
    assert "org/model" in result.output
    assert "detail: /cache/org/model" in result.output


def test_status_short_verbose_option_shows_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resource = HfSnapshotResource(repo="org/model", disk_gb=3.5)
    specs = [_spec(name="base", repo="logical-model", resources=(resource,))]
    manager = FakeSetupManager({resource.key: SetupStatus(True, "/cache/org/model")})
    _patch_status_inputs(monkeypatch, specs, manager)

    result = CliRunner().invoke(status_cli.status, ["-v"])

    assert result.exit_code == 0
    assert "repository: logical-model" in result.output


def test_status_dedupes_summary_resources_and_reports_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = HfSnapshotResource(repo="org/shared", disk_gb=4.0)
    specs = [
        _spec(name="small", repo="logical-small", resources=(shared,)),
        _spec(name="large", repo="logical-large", resources=(shared,)),
    ]
    manager = FakeSetupManager({shared.key: SetupStatus(False, "not found")})
    _patch_status_inputs(monkeypatch, specs, manager)

    result = CliRunner().invoke(status_cli.status, [])

    assert result.exit_code == 0
    assert "Models:    0 ready / 2 total" in result.output
    assert "Resources: 0 ready / 1 total" in result.output
    assert "Missing:   1" in result.output
    assert "Size:      - installed / ~4 GB total" in result.output
    assert result.output.count("Run: kiapi activate --repo org/shared") == 1


def test_status_marks_specs_without_setup_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = [_spec(name="local", repo="local", resources=())]
    manager = FakeSetupManager({})
    _patch_status_inputs(monkeypatch, specs, manager)

    result = CliRunner().invoke(status_cli.status, [])

    assert result.exit_code == 0
    assert "Models:    1 ready / 1 total" in result.output
    assert "local" in result.output
    assert "none" in result.output
    assert "0/0" in result.output


def _spec(
    *,
    name: str,
    repo: str,
    resources: tuple[SetupResource, ...],
    default: bool = False,
) -> ModelSpec:
    return ModelSpec(
        name=name,
        family="zimage",
        domain="image",
        repo=repo,
        module=ModuleType(f"test_{name}"),
        weight_gb=1.0,
        peak_headroom_gb=1.0,
        default=default,
        setup_resources=resources,
    )


def _patch_status_inputs(
    monkeypatch: pytest.MonkeyPatch,
    specs: list[ModelSpec],
    manager: FakeSetupManager,
) -> None:
    monkeypatch.setattr(status_cli, "register_all_capabilities", lambda: None)
    monkeypatch.setattr(status_cli.model_registry, "list_specs", lambda: specs)
    monkeypatch.setattr(status_cli, "SetupManager", lambda: manager)
