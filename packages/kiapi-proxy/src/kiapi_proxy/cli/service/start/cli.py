import click

from kiapi_proxy.cli.service import service_manager


@click.command(name="start")
def start() -> None:
    """Start the kiapi-proxy launchd user service."""
    plist_path = service_manager.get_plist_path()
    if not service_manager.is_installed():
        raise click.ClickException(f"Service is not installed: {plist_path}")
    if service_manager.is_loaded():
        raise click.ClickException(
            f"Service is already started: {service_manager.SERVICE_LABEL}"
        )

    try:
        service_manager.start()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Started {service_manager.SERVICE_LABEL}")
