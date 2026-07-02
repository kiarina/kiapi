import click
from kiarina.utils.app import configure

from kiapi_proxy.core.config import UserConfigError, load_user_settings

from .check.cli import check
from .config.cli import config_cli
from .run.cli import run
from .service.cli import service


@click.group()
def main() -> None:
    """kiapi-proxy command line interface."""
    configure("kiapi-proxy", "kiarina")
    try:
        load_user_settings()
    except UserConfigError as exc:
        raise click.ClickException(str(exc)) from exc


main.add_command(run)
main.add_command(check)
main.add_command(config_cli)
main.add_command(service)
