from pathlib import Path

from click.testing import CliRunner

from kiapi_proxy.cli.cli import main


def test_config_show_prints_settings_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "kiapi_proxy.api:\n  port: 9000\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "show"],
        env={"KIARINA_UTILS_APP_USER_CONFIG_DIR": str(config_dir)},
    )

    assert result.exit_code == 0
    assert result.output == "kiapi_proxy.api:\n  port: 9000\n"


def test_config_show_errors_when_missing(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "show"],
        env={"KIARINA_UTILS_APP_USER_CONFIG_DIR": str(tmp_path / "config")},
    )

    assert result.exit_code != 0
    assert "Settings file does not exist" in result.output
