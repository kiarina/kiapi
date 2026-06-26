"""Verify the filesystem-backed LocalRelay transport.

Start kiapi with LocalRelay first, for example:

    KIAPI_RELAY_LOCAL_NODE_ID=local \
    KIAPI_RELAY_LOCAL_ROOT=/tmp/kiapi/relay \
    KIAPI_RELAY_LOCAL_PREFIX=kiapi \
    uv run kiapi run --relay local

Then run:

    uv run python scripts/relay/verify_local.py
"""

from __future__ import annotations

import asyncio
import sys

from _helpers import assert_json, consume_body, relay_request, run_checks

from kiapi_relay import RelayFileBody, RelayRequest, RelayRequestError
from kiapi_relay.local import create_local_relay


async def main() -> int:
    fast = "--fast" in sys.argv
    client = create_local_relay()

    async def health() -> str:
        result = await relay_request(client, "GET", "/health", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "ok", body
        return "GET /health returned JSON"

    async def event_stream() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/chat/completions",
            headers={"Accept": "text/event-stream"},
            body={
                "messages": [{"role": "user", "content": "say hello briefly"}],
                "stream": True,
                "max_completion_tokens": 16,
            },
            timeout_s=1200.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert isinstance(body, list), body
        assert body and body[-1] == "[DONE]", body[-3:]
        return "text/event-stream was committed as JSON events"

    async def binary_body() -> str:
        result = await relay_request(
            client,
            "GET",
            "/docs",
            headers={"Accept": "text/html"},
            timeout_s=60.0,
        )
        assert result.status == 200, result.status
        assert isinstance(result.body, RelayFileBody), result.body
        content_type = result.body.content_type
        content = consume_body(result)
        assert content, "missing response body"
        assert content_type.startswith("text/html"), content_type
        return f"response body size={len(content)}"

    async def invalid_request() -> str:
        bad = RelayRequest.model_construct(
            method="GET",
            path="https://example.com/health",
            headers={},
            body=None,
            multipart=None,
        )
        try:
            await client.request(bad, timeout_s=30.0)
        except RelayRequestError as exc:
            assert exc.error.code == "invalid_relay_request", exc
            return "invalid non-local path failed through relay"
        raise AssertionError("invalid relay request unexpectedly succeeded")

    checks = [
        ("local health JSON", health),
        ("local event-stream conversion", event_stream),
        ("local binary response commit", binary_body),
        ("local invalid request failure", invalid_request),
    ]

    return await run_checks(checks, fast=fast)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
