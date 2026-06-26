import os
import tempfile
from pathlib import Path
from typing import Any

from .._schemas.relay_file_body import RelayFileBody
from .._schemas.relay_json_body import RelayJsonBody
from .._views.relay_response import RelayResponse


def build_relay_response(
    metadata: dict[str, Any],
    body_bytes: bytes | None,
) -> RelayResponse:
    """Rebuild a RelayResponse from transported metadata and optional body bytes.

    JSON and event-stream payloads are inlined under ``metadata["body"]``.
    Binary payloads are materialized to a temporary file whose lifetime the
    caller owns.
    """
    body: RelayJsonBody | RelayFileBody | None
    if "body" in metadata:
        body = RelayJsonBody(value=metadata["body"])
    elif body_bytes is not None:
        fd, raw_path = tempfile.mkstemp(prefix="kiapi-relay-", suffix=".body")
        with os.fdopen(fd, "wb") as file:
            file.write(body_bytes)
        body = RelayFileBody(
            path=Path(raw_path),
            content_type=str(metadata["content_type"]),
            size=int(metadata["size"]),
        )
    else:
        body = None

    return RelayResponse(
        status=int(metadata["status"]),
        headers=dict(metadata.get("headers") or {}),
        body=body,
    )
