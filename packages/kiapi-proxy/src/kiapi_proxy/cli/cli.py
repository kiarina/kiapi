import click
import uvicorn
from kiarina.utils.app import configure

from kiapi_relay import settings_manager as relay_settings_manager

from ..api import settings_manager


@click.group()
def main() -> None:
    """kiapi-proxy command line interface."""
    configure("kiapi-proxy", "kiarina")


@main.command()
@click.option("--host", type=str, help="Bind socket to this host")
@click.option("--port", type=int, help="Bind socket to this port")
@click.option(
    "--relay",
    type=str,
    help="Relay to forward requests through, for example: local, gcp",
)
def run(
    host: str | None,
    port: int | None,
    relay: str | None,
) -> None:
    """Run the kiapi-proxy server."""
    cli_args: dict[str, str | int] = {}

    if host is not None:
        cli_args["host"] = host
    if port is not None:
        cli_args["port"] = port

    if cli_args:
        settings_manager.cli_args = cli_args

    if relay is not None:
        # Forward through the named relay by setting it as the relay default.
        relay_settings_manager.cli_args = {"default": relay}

    settings = settings_manager.get_settings()

    from ..api.app import app

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
    )
