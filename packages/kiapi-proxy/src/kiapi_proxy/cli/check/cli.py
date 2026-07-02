import asyncio
import json
import uuid

import click

from kiapi_relay import (
    Relay,
    RelayRequest,
    RelayRequestError,
    RelayResponse,
    relay_registry,
)

from ...api import settings_manager


@click.command()
@click.option(
    "--relay",
    type=str,
    help="Relay to check through, for example: local, gcp. "
    "Defaults to the configured proxy/relay default.",
)
@click.option(
    "--path",
    type=str,
    default="/health",
    show_default=True,
    help="API path to request on the kiapi node.",
)
@click.option(
    "--timeout",
    "timeout_s",
    type=float,
    help="Seconds to wait for the relayed response.",
)
def check(
    relay: str | None,
    path: str,
    timeout_s: float | None,
) -> None:
    """Check connectivity to a live kiapi node over the relay.

    Sends a single request through the relay without starting the proxy server
    and reports the response, so you can confirm the relay link to kiapi works.
    """
    settings = settings_manager.get_settings()

    # Explicit --relay wins; otherwise fall back to the proxy's configured relay,
    # then to the relay's own default (relay_registry.resolve handles None).
    specifier = relay if relay is not None else settings.relay
    timeout = timeout_s if timeout_s is not None else settings.request_timeout_s

    try:
        relay_instance = relay_registry.resolve(specifier)
    except Exception as exc:
        raise click.ClickException(f"Failed to resolve relay: {exc}") from exc

    # A short-lived node ID just to receive this one response; the proxy service
    # (if running) keeps its own persistent node ID untouched.
    relay_instance.node_id = uuid.uuid4().hex[:12]

    click.echo(f"checking {relay_instance.name} relay -> {path} ...")

    try:
        response = asyncio.run(
            _request(relay_instance, path, timeout),
        )
    except RelayRequestError as exc:
        raise click.ClickException(
            f"[failed] relay error: {exc.error.code}: {exc.error.message}"
        ) from exc
    except TimeoutError as exc:
        raise click.ClickException(f"[failed] {exc}") from exc
    except Exception as exc:
        raise click.ClickException(f"[failed] {exc}") from exc

    ok = 200 <= response.status < 400
    mark = "ok" if ok else "failed"
    click.echo(f"  [{mark}] HTTP {response.status}")
    click.echo(f"  {_format_body(response)}")

    if not ok:
        raise click.ClickException(f"relay check returned HTTP {response.status}")


async def _request(relay_instance: Relay, path: str, timeout_s: float) -> RelayResponse:
    request = RelayRequest(method="GET", path=path)
    return await relay_instance.request(request, timeout_s=timeout_s)


def _format_body(response: RelayResponse) -> str:
    body = response.body
    if body is None:
        return "(no body)"

    value = getattr(body, "value", None)
    if value is not None:
        return json.dumps(value, ensure_ascii=False)

    return repr(body)
