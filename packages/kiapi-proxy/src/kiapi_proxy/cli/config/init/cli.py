from pathlib import Path

import click

from kiapi_proxy.core.config import get_user_settings_path

_DEFAULT_USER_SETTINGS = """# kiapi-proxy user settings
kiapi_proxy.api:
  host: 127.0.0.1
  port: 8080
  relay: null
  request_timeout_s: 1800.0

kiapi_relay:
  default: local
"""


@click.command(name="init")
def init() -> None:
    """Create the user settings file if it does not exist."""
    path = _init_user_settings()
    click.echo(str(path))


def _init_user_settings() -> Path:
    path = get_user_settings_path()
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_DEFAULT_USER_SETTINGS, encoding="utf-8")
    return path
