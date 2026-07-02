"""Shared helpers for relay verification scripts.

These wrap the public relay client (``Relay.request``) with the small
assertion and formatting utilities the verify scripts rely on.
"""

from __future__ import annotations

import base64
import os
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any

import httpx

from kiapi_relay import (
    Relay,
    RelayFileBody,
    RelayJsonBody,
    RelayRequest,
    RelayResponse,
    get_or_create_node_id,
)


def load_user_settings() -> None:
    """Load the kiapi user settings into the relay settings managers.

    The relay verify scripts run standalone (``uv run python
    scripts/relay/verify_<relay>.py``), not through the kiapi CLI, so the
    settings that ``kiapi config edit`` writes to ``~/.config/kiapi/settings.yaml``
    are never applied to the relay ``settings_manager`` instances. Mirror what
    the kiapi CLI does at startup before constructing a relay client, otherwise
    required fields (for example the GCP relay ``database_url`` / ``bucket``)
    look unset even though the user configured them.
    """
    from kiarina.utils.app import configure

    from kiapi.core.config import load_user_settings as _load_user_settings

    configure("kiapi", "kiarina")
    _load_user_settings()


def assign_verify_node_id(client: Relay) -> None:
    """Give the verify client its own persistent relay node id.

    The relay client must carry a ``node_id`` distinct from the server's so the
    server can route responses back to it. The verify client is not kiapi or
    kiapi-proxy, so it keeps its own id under the verify data directory rather
    than borrowing either server's identity.
    """
    data_dir = Path(os.environ.get("KIAPI_VERIFY_DIR", ".verify")) / "relay-node"
    client.node_id = get_or_create_node_id(data_dir)


def build_request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    multipart: dict[str, object] | None = None,
) -> RelayRequest:
    return RelayRequest.model_validate(
        {
            "method": method,
            "path": path,
            "headers": headers or {},
            "body": body,
            "multipart": multipart,
        }
    )


async def relay_request(
    client: Relay,
    method: str,
    path: str,
    *,
    timeout_s: float,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    multipart: dict[str, object] | None = None,
) -> RelayResponse:
    return await client.request(
        build_request(method, path, headers=headers, body=body, multipart=multipart),
        timeout_s=timeout_s,
    )


async def ensure_relay_ready(
    client: Relay,
    expect_name: str,
    *,
    timeout_s: float = 15.0,
) -> bool:
    try:
        result = await relay_request(client, "GET", "/health", timeout_s=timeout_s)
    except TimeoutError:
        print(f"[SKIP] no server is watching the {expect_name} relay")
        return False

    relay = assert_json(result).get("relay")
    if relay is None:
        print(f"[SKIP] server is not running the {expect_name} relay")
        return False
    if relay.get("name") != expect_name or not relay.get("running"):
        print(f"[SKIP] server relay is not a running {expect_name} relay: {relay}")
        return False
    return True


def assert_json(result: RelayResponse) -> Any:
    if not isinstance(result.body, RelayJsonBody):
        raise AssertionError(f"expected JSON body, got {type(result.body).__name__}")
    return result.body.value


def consume_body(result: RelayResponse) -> bytes:
    """Read a binary response body and remove its temporary file."""
    if not isinstance(result.body, RelayFileBody):
        raise AssertionError(f"expected binary body, got {type(result.body).__name__}")
    try:
        return result.body.path.read_bytes()
    finally:
        result.body.path.unlink(missing_ok=True)


def data_url(path: Path, content_type: str) -> str:
    return (
        f"data:{content_type};base64,"
        f"{base64.b64encode(path.read_bytes()).decode('ascii')}"
    )


def query_path(path: str, **params: str) -> str:
    query = httpx.QueryParams(params)
    return f"{path}?{query}" if query else path


async def run_checks(
    checks: Sequence[tuple[str, Callable[[], Awaitable[str | None]]]],
    *,
    fast: bool = False,
) -> int:
    failures: list[str] = []
    for name, fn in checks:
        started = time.time()
        try:
            detail = await fn()
            print(f"[OK] {name} ({time.time() - started:.1f}s) {detail or ''}".rstrip())
        except Exception as exc:
            failures.append(name)
            print(f"[NG] {name} ({time.time() - started:.1f}s) {exc}")
        if fast:
            break

    print()
    print(f"{len(checks) - len(failures)}/{len(checks)} checks passed")
    if failures:
        print("Failed checks:")
        for failure in failures:
            print(f"  - {failure}")
    return 1 if failures else 0
