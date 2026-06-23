from pathlib import Path

from click.testing import CliRunner

from kiapi.cli.cli import main


def test_config_show_prints_settings_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "settings.yaml"
    path.write_text("kiapi.api:\n  port: 9000\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "show"],
        env={"KIAPI_USER_CONFIG_DIR": str(config_dir)},
    )

    assert result.exit_code == 0
    assert result.output == "kiapi.api:\n  port: 9000\n"
