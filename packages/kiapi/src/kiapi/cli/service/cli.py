import click

from .install.cli import install
from .start.cli import start
from .status.cli import status
from .stop.cli import stop
from .uninstall.cli import uninstall


@click.group(name="service")
def service() -> None:
    """Manage the kiapi launchd user service."""


service.add_command(install)
service.add_command(start)
service.add_command(stop)
service.add_command(status)
service.add_command(uninstall)
