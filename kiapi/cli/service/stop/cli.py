import click

from kiapi.cli.service import service_manager


@click.command(name="stop")
def stop() -> None:
    """Stop the kiapi launchd user service."""
    if not service_manager.is_loaded():
        raise click.ClickException(
            f"Service is already stopped: {service_manager.SERVICE_LABEL}"
        )

    try:
        service_manager.stop()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Stopped {service_manager.SERVICE_LABEL}")
