from pathlib import Path

from click.testing import CliRunner

from kiapi.cli.cli import main


def test_config_edit_suggests_init_when_settings_file_is_missing(
    tmp_path: Path,
) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "edit"],
        env={"KIAPI_USER_CONFIG_DIR": str(tmp_path / "config")},
    )

    assert result.exit_code != 0
    assert "kiapi config init" in result.output


def test_config_edit_opens_existing_settings_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "settings.yaml"
    path.write_text("kiapi.api:\n  port: 9000\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "edit"],
        env={
            "EDITOR": "true",
            "KIAPI_USER_CONFIG_DIR": str(config_dir),
            "VISUAL": "",
        },
    )

    assert result.exit_code == 0
