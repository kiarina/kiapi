from pathlib import Path

import pytest

from kiapi.cli.service import service_manager
from kiapi.cli.service.status import cli as status_cli
from tests.cli.service.conftest import invoke_service, write_service_plist


def test_service_status_shows_paths_and_log_tails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_service_plist(tmp_path)
    stdout = tmp_path / "out.log"
    stderr = tmp_path / "err.log"
    stdout.write_text("out1\nout2\n", encoding="utf-8")
    stderr.write_text("err1\nerr2\n", encoding="utf-8")
    monkeypatch.setattr(service_manager, "is_loaded", lambda: True)
    monkeypatch.setattr(service_manager, "get_stdout_path", lambda: stdout)
    monkeypatch.setattr(service_manager, "get_stderr_path", lambda: stderr)
    monkeypatch.setattr(status_cli, "_check_health", lambda: (True, "healthy"))

    result = invoke_service(tmp_path, "status")

    assert result.exit_code == 0
    assert "Installed: yes" in result.output
    assert "Loaded:    yes" in result.output
    assert f"stdout:    {stdout}" in result.output
    assert f"stderr:    {stderr}" in result.output
    assert "Health:    ok - healthy" in result.output
    assert "  out1" in result.output
    assert "  out2" in result.output
    assert "  err1" in result.output
    assert "  err2" in result.output
