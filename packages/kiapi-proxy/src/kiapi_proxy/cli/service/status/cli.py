import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import click

from kiapi_proxy.api import settings_manager as api_settings_manager
from kiapi_proxy.cli.service import service_manager

_LOG_TAIL_LINES = 10


@click.command(name="status")
def status() -> None:
    """Show kiapi-proxy launchd service status and recent logs."""
    plist_path = service_manager.get_plist_path()
    loaded = service_manager.is_loaded()

    click.echo("kiapi-proxy service status")
    click.echo(f"Label:     {service_manager.SERVICE_LABEL}")
    click.echo(f"Installed: {'yes' if service_manager.is_installed() else 'no'}")
    click.echo(f"Loaded:    {'yes' if loaded else 'no'}")
    click.echo(f"Plist:     {plist_path}")
    click.echo(f"stdout:    {service_manager.get_stdout_path()}")
    click.echo(f"stderr:    {service_manager.get_stderr_path()}")

    if loaded:
        healthy, detail = _check_health()
        click.echo(f"Health:    {'ok' if healthy else 'error'} - {detail}")
    else:
        click.echo("Health:    skipped - service is not loaded")

    _echo_log_tail("stdout", service_manager.get_stdout_path())
    _echo_log_tail("stderr", service_manager.get_stderr_path())


def _check_health() -> tuple[bool, str]:
    settings = api_settings_manager.get_settings()
    # The proxy relays every path, so /health is forwarded to kiapi. A response
    # confirms both the proxy process and the relay link to kiapi are alive.
    url = f"http://localhost:{settings.port}/health"

    try:
        with urlopen(url, timeout=5.0) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return False, f"{url} returned HTTP {exc.code}"
    except URLError as exc:
        return False, f"{url} is unavailable: {exc.reason}"
    except TimeoutError:
        return False, f"{url} timed out"

    try:
        data: Any = json.loads(body)
    except json.JSONDecodeError:
        return True, f"{url} responded: {body[:200]}"

    if isinstance(data, dict):
        status = data.get("status") or data.get("state") or "ok"
        return True, f"{url} responded: {status}"

    return True, f"{url} responded"


def _echo_log_tail(label: str, path: Path) -> None:
    lines = _tail_file(path, _LOG_TAIL_LINES)
    click.echo()
    click.echo(f"{label} tail ({path})")
    if not lines:
        click.echo("  (empty)")
        return
    for line in lines:
        click.echo(f"  {line}")


def _tail_file(path: Path, line_count: int) -> list[str]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-line_count:]
