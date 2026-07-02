from pathlib import Path

from tests.cli.service.conftest import invoke_service, write_service_plist


def test_service_install_creates_plist_and_log_dir(tmp_path: Path) -> None:
    result = invoke_service(tmp_path, "install")

    assert result.exit_code == 0
    plist = (
        tmp_path / "Library" / "LaunchAgents" / "io.github.kiarina.kiapi-proxy.plist"
    )
    assert plist.exists()
    assert b"<string>kiapi_proxy</string>" in plist.read_bytes()
    assert "Installed io.github.kiarina.kiapi-proxy" in result.output
    assert "/tmp/kiapi-proxy/service/out.log" in result.output
    assert "/tmp/kiapi-proxy/service/err.log" in result.output


def test_service_install_errors_when_already_installed(tmp_path: Path) -> None:
    write_service_plist(tmp_path)

    result = invoke_service(tmp_path, "install")

    assert result.exit_code != 0
    assert "Service is already installed" in result.output
