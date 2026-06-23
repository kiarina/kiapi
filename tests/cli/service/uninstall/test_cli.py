from pathlib import Path

import pytest

from kiapi.cli.service import service_manager
from tests.cli.service.conftest import invoke_service, write_service_plist


def test_service_uninstall_errors_when_missing(tmp_path: Path) -> None:
    result = invoke_service(tmp_path, "uninstall")

    assert result.exit_code != 0
    assert "Service is not installed" in result.output


def test_service_uninstall_errors_when_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_service_plist(tmp_path)
    monkeypatch.setattr(service_manager, "is_loaded", lambda: True)

    result = invoke_service(tmp_path, "uninstall")

    assert result.exit_code != 0
    assert "Stop it before uninstalling" in result.output
