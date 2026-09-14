from pathlib import Path

import pytest

from kiapi.cli.service import service_manager
from tests.cli.service.conftest import invoke_service


def test_service_stop_errors_when_already_stopped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service_manager, "is_loaded", lambda: False)

    result = invoke_service(tmp_path, "stop")

    assert result.exit_code != 0
    assert "Service is already stopped" in result.output
