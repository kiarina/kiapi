import click

from kiapi.cli.service import service_manager


@click.command(name="install")
def install() -> None:
    """Install the kiapi launchd user service."""
    plist_path = service_manager.get_plist_path()
    if service_manager.is_installed():
        raise click.ClickException(f"Service is already installed: {plist_path}")

    service_manager.install()
    click.echo(f"Installed {service_manager.SERVICE_LABEL}")
    click.echo(f"Plist: {plist_path}")
    click.echo(f"stdout: {service_manager.get_stdout_path()}")
    click.echo(f"stderr: {service_manager.get_stderr_path()}")
