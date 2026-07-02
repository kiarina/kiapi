import click
from pydantic_settings_manager import generate_user_configs_yaml

_SETTINGS_IMPORT_PATHS = [
    "kiapi_proxy.api",
    "kiarina.utils.app",
    "kiapi_relay",
    "kiapi_relay.impl.local",
    "kiapi_relay.impl.gcp",
    "kiarina.lib.google",
]


@click.command(name="template")
def template() -> None:
    """Show the full user settings template."""
    click.echo(_generate_user_settings_template())


def _generate_user_settings_template() -> str:
    return generate_user_configs_yaml(_SETTINGS_IMPORT_PATHS)
