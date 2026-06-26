"""Verify the GCPRelay transport.

Start kiapi with GCPRelay first, for example:

    KIAPI_RELAY_GCP_NODE_ID=studio-1 \
    KIAPI_RELAY_GCP_DATABASE_URL=https://PROJECT.firebaseio.com \
    KIAPI_RELAY_GCP_BUCKET=PRIVATE_RELAY_BUCKET \
    KIAPI_RELAY_GCP_PREFIX=private/kiapi \
    uv run kiapi run --relay gcp

Then run this from an environment with the same GCP settings and credentials:

    uv run python scripts/relay/verify_gcp.py
"""

from __future__ import annotations

import sys

from _client import GCPRelayClient, assert_json, run_checks


def main() -> int:
    fast = "--fast" in sys.argv
    client = GCPRelayClient()

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
        ("gcp health JSON", health),
        ("gcp event-stream conversion", event_stream),
        ("gcp binary response commit", binary_body),
        ("gcp invalid request failure", invalid_request),
    ]

    try:
        return run_checks(checks, fast=fast)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
