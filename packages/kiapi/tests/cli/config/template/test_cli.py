from pathlib import Path

from click.testing import CliRunner

from kiapi.cli.cli import main


def test_config_template_prints_generated_template(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["config", "template"],
        env={"KIAPI_USER_CONFIG_DIR": str(tmp_path / "config")},
    )

    assert result.exit_code == 0
    assert "kiapi.api:" in result.output
    assert "kiapi.capabilities.web:" in result.output
