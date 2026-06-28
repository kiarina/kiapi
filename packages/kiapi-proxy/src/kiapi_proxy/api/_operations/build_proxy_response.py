import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from starlette.background import BackgroundTask
from starlette.responses import FileResponse, Response, StreamingResponse

from kiapi_relay import RelayFileBody, RelayJsonBody, RelayResponse

# Set explicitly from the relayed body; never forwarded verbatim.
_OMIT_HEADERS = {"content-type", "content-length"}


def build_proxy_response(relay_response: RelayResponse) -> Response:
    """Translate a ``RelayResponse`` back into an outgoing HTTP response.

    - JSON bodies are returned as-is.
    - JSON bodies whose original content type was ``text/event-stream`` are
      re-serialized into a Server-Sent Events stream.
    - File bodies are streamed from their temporary file, which is removed once
      the response has been sent.
    """
    headers = {
        key: value
        for key, value in relay_response.headers.items()
        if key.lower() not in _OMIT_HEADERS
    }
    content_type = relay_response.headers.get("content-type", "")
    body = relay_response.body

    if body is None:
        return Response(status_code=relay_response.status, headers=headers)

    if isinstance(body, RelayFileBody):
        return FileResponse(
            body.path,
            status_code=relay_response.status,
            media_type=body.content_type,
            headers=headers,
            background=BackgroundTask(_unlink, body.path),
        )

    if isinstance(body, RelayJsonBody):
        if content_type.split(";", 1)[0].strip().lower() == "text/event-stream":
            return StreamingResponse(
                _iter_sse(body.value),
                status_code=relay_response.status,
                media_type="text/event-stream",
                headers=headers,
            )

        payload = json.dumps(
            body.value, ensure_ascii=False, separators=(",", ":")
        ).encode()
        return Response(
            content=payload,
            status_code=relay_response.status,
            media_type=content_type or "application/json",
            headers=headers,
        )

    raise TypeError(f"unsupported relay body: {type(body).__name__}")


def _iter_sse(value: Any) -> Iterator[str]:
    events = value if isinstance(value, list) else [value]
    for event in events:
        payload = (
            event if isinstance(event, str) else json.dumps(event, ensure_ascii=False)
        )
        yield f"data: {payload}\n\n"


def _unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
