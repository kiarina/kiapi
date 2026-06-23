from pathlib import Path

import pytest

from kiapi.cli.service import service_manager
from tests.cli.service.conftest import (
    invoke_service,
    record_launchctl,
    write_service_plist,
)


def test_service_start_errors_when_not_installed(tmp_path: Path) -> None:
    result = invoke_service(tmp_path, "start")

    assert result.exit_code != 0
    assert "Service is not installed" in result.output


def test_service_start_errors_when_already_started(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_service_plist(tmp_path)
    monkeypatch.setattr(service_manager, "is_loaded", lambda: True)

    result = invoke_service(tmp_path, "start")

    assert result.exit_code != 0
    assert "Service is already started" in result.output


def test_service_start_bootstraps_unloaded_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_service_plist(tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(service_manager, "is_loaded", lambda: False)
    monkeypatch.setattr(service_manager, "get_launchd_domain", lambda: "gui/501")
    monkeypatch.setattr(
        service_manager,
        "run_launchctl",
        lambda args: record_launchctl(calls, args),
    )

    result = invoke_service(tmp_path, "start")

    assert result.exit_code == 0
    assert calls == [
        [
            "bootstrap",
            "gui/501",
            str(
                tmp_path / "Library" / "LaunchAgents" / "io.github.kiarina.kiapi.plist"
            ),
        ],
        ["kickstart", "-k", "gui/501/io.github.kiarina.kiapi"],
    ]
    assert "Started io.github.kiarina.kiapi" in result.output
