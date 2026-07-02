from click.testing import CliRunner

from kiapi_proxy.cli.cli import main


def test_config_template_lists_relevant_modules() -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["config", "template"])

    assert result.exit_code == 0
    assert "kiapi_proxy.api:" in result.output
    assert "kiapi_relay:" in result.output
    assert "kiapi_relay.impl.gcp:" in result.output
