import click
from kiarina.utils.app import configure

from kiapi.core.config import UserConfigError, load_user_settings

from .activate.cli import activate
from .check.cli import check
from .config.cli import config_cli
from .deactivate.cli import deactivate
from .run.cli import run
from .service.cli import service
from .status.cli import status


@click.group()
def main() -> None:
    """kiapi command line interface."""
    configure("kiapi", "kiarina")
    try:
        load_user_settings()
    except UserConfigError as exc:
        raise click.ClickException(str(exc)) from exc


main.add_command(run)
main.add_command(status)
main.add_command(activate)
main.add_command(deactivate)
main.add_command(check)
main.add_command(config_cli)
main.add_command(service)
