import plistlib
from pathlib import Path

from pytest import MonkeyPatch

from tests.cli.service.conftest import invoke_service, write_service_plist


def test_service_install_creates_plist_and_log_dir(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / ".local" / "share"))

    result = invoke_service(tmp_path, "install")

    assert result.exit_code == 0
    plist = tmp_path / "Library" / "LaunchAgents" / "io.github.kiarina.kiapi.plist"
    assert plist.exists()
    assert b"<string>kiapi</string>" in plist.read_bytes()
    data = plistlib.loads(plist.read_bytes())
    assert data["EnvironmentVariables"] == {
        "PYTHONUNBUFFERED": "1",
        "XDG_CONFIG_HOME": str(tmp_path / ".config"),
        "XDG_DATA_HOME": str(tmp_path / ".local" / "share"),
    }
    assert "Installed io.github.kiarina.kiapi" in result.output
    assert "/tmp/kiapi/service/out.log" in result.output
    assert "/tmp/kiapi/service/err.log" in result.output


def test_service_install_errors_when_already_installed(tmp_path: Path) -> None:
    write_service_plist(tmp_path)

    result = invoke_service(tmp_path, "install")

    assert result.exit_code != 0
    assert "Service is already installed" in result.output
