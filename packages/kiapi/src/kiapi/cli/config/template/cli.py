import click
from pydantic_settings_manager import generate_user_configs_yaml

_SETTINGS_IMPORT_PATHS = [
    "kiapi.api",
    "kiapi.core.logging",
    "kiarina.utils.app",
    "kiapi.core.workdir",
    "kiapi.core.file",
    "kiapi.core.memory",
    "kiapi.core.worker",
    "kiapi.core.net",
    "kiapi_relay",
    "kiapi_relay.impl.gcp",
    "kiapi_relay.impl.local",
    "kiarina.lib.google",
    "kiapi.capabilities.chat",
    "kiapi.capabilities.embedding",
    "kiapi.capabilities.depthpro",
    "kiapi.capabilities.ernie",
    "kiapi.capabilities.flux2",
    "kiapi.capabilities.ideogram4",
    "kiapi.capabilities.qwen",
    "kiapi.capabilities.seedvr2",
    "kiapi.capabilities.zimage",
    "kiapi.capabilities.acestep",
    "kiapi.capabilities.audiogen",
    "kiapi.capabilities.ltx2",
    "kiapi.capabilities.web",
]


@click.command(name="template")
def template() -> None:
    """Show the full user settings template."""
    click.echo(_generate_user_settings_template())


def _generate_user_settings_template() -> str:
    return generate_user_configs_yaml(_SETTINGS_IMPORT_PATHS)
