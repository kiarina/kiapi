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

import asyncio
import base64
import sys
from typing import Any

from _helpers import (
    assert_json,
    assign_verify_node_id,
    consume_body,
    ensure_relay_ready,
    load_user_settings,
    relay_request,
    run_checks,
)

from kiapi_relay import RelayFileBody, RelayRequest, RelayRequestError
from kiapi_relay.impl.gcp import create_gcp_relay

UPLOAD_BYTES = b"relay multipart upload\n"


async def main() -> int:
    fast = "--fast" in sys.argv
    load_user_settings()
    client = create_gcp_relay()
    assign_verify_node_id(client)
    state: dict[str, Any] = {}

    if not await ensure_relay_ready(client, "gcp"):
        await client.aclose()
        return 0

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

    async def files_list() -> str:
        result = await relay_request(client, "GET", "/v1/files", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["object"] == "list", body
        return f"{len(body['data'])} files listed"

    async def jobs_list() -> str:
        result = await relay_request(client, "GET", "/v1/jobs", timeout_s=60.0)
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["object"] == "list", body
        return f"{len(body['data'])} jobs listed"

    async def files_upload() -> str:
        result = await relay_request(
            client,
            "POST",
            "/v1/files",
            headers={"Accept": "application/json"},
            multipart={
                "files": [
                    {
                        "field": "file",
                        "filename": "relay-upload.txt",
                        "content_type": "text/plain",
                        "content_base64": base64.b64encode(UPLOAD_BYTES).decode(
                            "ascii"
                        ),
                    }
                ]
            },
            timeout_s=60.0,
        )
        body = assert_json(result)
        assert result.status == 200, result.status
        assert body["file_id"], body
        assert body["filename"] == "relay-upload.txt", body
        assert body["content_type"] == "text/plain", body
        state["uploaded_file_id"] = body["file_id"]
        return f"file_id={body['file_id']}"

    async def file_metadata_download_delete() -> str:
        file_id = state.get("uploaded_file_id")
        assert file_id, "no file_id captured from earlier checks"
        metadata = await relay_request(
            client, "GET", f"/v1/files/{file_id}", timeout_s=60.0
        )
        body = assert_json(metadata)
        assert metadata.status == 200, metadata.status
        assert body["file_id"] == file_id, body

        download = await relay_request(
            client, "GET", f"/v1/files/{file_id}/download", timeout_s=120.0
        )
        assert download.status == 200, download.status
        content = consume_body(download)
        assert content == UPLOAD_BYTES, content

        deleted = await relay_request(
            client, "DELETE", f"/v1/files/{file_id}", timeout_s=60.0
        )
        deleted_body = assert_json(deleted)
        assert deleted.status == 200, deleted.status
        assert deleted_body["deleted"] is True, deleted_body
        return f"metadata/download/delete {file_id}"

    checks = [
        ("gcp health JSON", health),
        ("gcp event-stream conversion", event_stream),
        ("gcp binary response commit", binary_body),
        ("gcp invalid request failure", invalid_request),
        ("gcp /v1/files list", files_list),
        ("gcp /v1/jobs list", jobs_list),
        ("gcp /v1/files upload multipart", files_upload),
        ("gcp /v1/files metadata/download/delete", file_metadata_download_delete),
    ]

    try:
        return await run_checks(checks, fast=fast)
    finally:
        await client.aclose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
