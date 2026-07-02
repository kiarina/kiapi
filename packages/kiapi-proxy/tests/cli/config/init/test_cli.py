from pathlib import Path

from click.testing import CliRunner

from kiapi_proxy.cli.cli import main


def test_config_init_creates_settings_file(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "init"],
        env={"KIARINA_UTILS_APP_USER_CONFIG_DIR": str(tmp_path / "config")},
    )

    assert result.exit_code == 0
    path = tmp_path / "config" / "settings.yaml"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == (
        "# kiapi-proxy user settings\n"
        "kiapi_proxy.api:\n"
        "  host: 127.0.0.1\n"
        "  port: 8080\n"
        "  relay: null\n"
        "  request_timeout_s: 1800.0\n"
        "\n"
        "kiapi_relay:\n"
        "  default: local\n"
    )


def test_config_init_keeps_existing_settings_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "settings.yaml"
    path.write_text("kiapi_proxy.api:\n  port: 9000\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "init"],
        env={"KIARINA_UTILS_APP_USER_CONFIG_DIR": str(config_dir)},
    )

    assert result.exit_code == 0
    assert path.read_text(encoding="utf-8") == "kiapi_proxy.api:\n  port: 9000\n"
