from pathlib import Path

from tests.cli.service.conftest import invoke_service, write_service_plist


def test_service_show_prints_plist(tmp_path: Path) -> None:
    write_service_plist(tmp_path)

    result = invoke_service(tmp_path, "show")

    assert result.exit_code == 0
    assert result.output == "installed"


def test_service_show_errors_when_not_installed(tmp_path: Path) -> None:
    result = invoke_service(tmp_path, "show")

    assert result.exit_code != 0
    assert "Service is not installed" in result.output
