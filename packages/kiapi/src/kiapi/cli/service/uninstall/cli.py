import click

from kiapi.cli.service import service_manager


@click.command(name="uninstall")
def uninstall() -> None:
    """Remove the kiapi launchd user service."""
    plist_path = service_manager.get_plist_path()
    if not service_manager.is_installed():
        raise click.ClickException(f"Service is not installed: {plist_path}")
    if service_manager.is_loaded():
        raise click.ClickException("Service is running. Stop it before uninstalling.")

    service_manager.uninstall()
    click.echo(f"Removed {plist_path}")
