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

import sys

from _client import LocalRelayClient, assert_json, run_checks


def main() -> int:
    fast = "--fast" in sys.argv
    client = LocalRelayClient()

    def health() -> str:
        result = client.request("GET", "/health", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["status"] == "ok", body
        return "GET /health returned JSON"

    def event_stream() -> str:
        result = client.request(
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

    def binary_body() -> str:
        result = client.request(
            "GET",
            "/docs",
            headers={"Accept": "text/html"},
            timeout_s=60.0,
        )
        assert result.status == 200, result.status
        assert result.body, "missing response.body"
        assert result.content_type.startswith("text/html"), result.content_type
        return f"response.body size={len(result.body)}"

    def invalid_request() -> str:
        try:
            client.request("GET", "https://example.com/health", timeout_s=30.0)
        except RuntimeError as exc:
            assert "invalid_relay_request" in str(exc), exc
            return "invalid non-local path failed through relay"
        raise AssertionError("invalid relay request unexpectedly succeeded")

    checks = [
        ("local health JSON", health),
        ("local event-stream conversion", event_stream),
        ("local binary response commit", binary_body),
        ("local invalid request failure", invalid_request),
    ]

    try:
        return run_checks(checks, fast=fast)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
