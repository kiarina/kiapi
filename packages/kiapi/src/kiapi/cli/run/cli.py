import os

import click
import uvicorn

from kiapi.api import settings_manager as api_settings_manager
from kiapi.cli import register_all_capabilities
from kiapi.core.logging import get_log_level
from kiapi.core.logging import settings_manager as logging_settings_manager
from kiapi_relay import settings_manager as relay_settings_manager


@click.command()
@click.option("--host", type=str, help="Bind socket to this host")
@click.option("--port", type=int, help="Bind socket to this port")
@click.option(
    "--relay",
    type=str,
    help="Start a relay, for example: gcp. Pass 'none' to disable the relay.",
)
@click.option("--debug", is_flag=True, help="Enable debug logging and hot reload")
def run(
    host: str | None,
    port: int | None,
    relay: str | None,
    debug: bool,
) -> None:
    """Run the kiapi API server."""
    api_cli_args: dict[str, str | int] = {}

    if host is not None:
        api_cli_args["host"] = host
    if port is not None:
        api_cli_args["port"] = port

    if api_cli_args:
        api_settings_manager.cli_args = api_cli_args

    if relay is not None:
        relay_settings_manager.cli_args = {
            "default": None if relay == "none" else relay
        }

    settings = api_settings_manager.get_settings()

    if debug:
        logging_settings_manager.cli_args = {"log_level": "DEBUG"}
        # The reload subprocess re-imports the app fresh and does not inherit
        # in-process cli_args, so propagate the log level via the environment.
        os.environ["KIAPI_LOG_LEVEL"] = "DEBUG"

        if relay is not None:
            os.environ["KIAPI_RELAY_DEFAULT"] = relay

        # Hot reload requires an import string (the worker subprocess
        # re-imports the app), so use the ASGI factory that registers
        # capabilities on import.
        uvicorn.run(
            "kiapi.cli.run.asgi:create_app",
            factory=True,
            reload=True,
            reload_dirs=["kiapi"],
            host=settings.host,
            port=settings.port,
            log_level=get_log_level(),
        )
        return

    register_all_capabilities()

    from kiapi.api.app import app

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=get_log_level(),
    )
