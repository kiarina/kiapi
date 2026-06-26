import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from .._schemas.relay_file_body import RelayFileBody
from .._schemas.relay_json_body import RelayJsonBody
from .._types.relay import Relay
from .._types.relay_delivery import RelayDelivery
from .._views.relay_error import RelayError
from .._views.relay_request import RelayRequest
from .._views.relay_response import RelayResponse

logger = logging.getLogger(__name__)

_HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class RelayRunner:
    def __init__(self, relay: Relay, app: FastAPI) -> None:
        self._relay = relay
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://kiapi.internal",
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="kiapi-relay")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._client.aclose()

    async def _run(self) -> None:
        try:
            async for delivery in self._relay.watch():
                await self._process(delivery)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Relay watch loop stopped unexpectedly")

    async def _process(self, delivery: RelayDelivery) -> None:
        file_path: Path | None = None
        try:
            await delivery.start()
            response, file_path = await self._dispatch(delivery.request)
            await delivery.complete(response)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Relay delivery failed")
            await delivery.fail(
                RelayError(
                    code=_error_code(exc),
                    message=str(exc) or exc.__class__.__name__,
                    retryable=_is_retryable(exc),
                )
            )
        finally:
            if file_path is not None:
                file_path.unlink(missing_ok=True)

    async def _dispatch(
        self, request: RelayRequest
    ) -> tuple[RelayResponse, Path | None]:
        headers = _relay_headers(request)
        if request.multipart is None:
            response = await self._client.request(
                request.method,
                request.path,
                headers=headers,
                json=request.body,
            )
        else:
            response = await self._client.request(
                request.method,
                request.path,
                headers=headers,
                data=request.multipart.fields,
                files=[
                    (
                        file.field,
                        (file.filename, file.content(), file.content_type),
                    )
                    for file in request.multipart.files
                ],
            )
        content = await response.aread()
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        response_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in _HOP_BY_HOP_HEADERS
        }

        body: RelayJsonBody | RelayFileBody | None
        if not content:
            body = None
            file_path = None
        elif content_type == "text/event-stream":
            body = RelayJsonBody(value=_parse_event_stream(content))
            file_path = None
        elif content_type == "application/json" or content_type.endswith("+json"):
            body = RelayJsonBody(value=response.json())
            file_path = None
        else:
            fd, raw_path = tempfile.mkstemp(prefix="kiapi-relay-", suffix=".body")
            file_path = Path(raw_path)
            with os.fdopen(fd, "wb") as file:
                file.write(content)
            body = RelayFileBody(
                path=file_path,
                content_type=content_type or "application/octet-stream",
                size=len(content),
            )

        return (
            RelayResponse(
                status=response.status_code,
                headers=response_headers,
                body=body,
            ),
            file_path,
        )


def _relay_headers(request: RelayRequest) -> dict[str, str]:
    excluded = set(_HOP_BY_HOP_HEADERS)
    if request.multipart is not None:
        excluded.add("content-type")
    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in excluded
    }


def _parse_event_stream(content: bytes) -> list[Any]:
    events: list[Any] = []
    for line in content.decode("utf-8").splitlines():
        if not line.startswith("data:"):
            continue
        value = line[5:].strip()
        if value == "[DONE]":
            events.append(value)
            continue
        try:
            events.append(json.loads(value))
        except json.JSONDecodeError:
            events.append(value)
    return events


def _error_code(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "relay_timeout"
    if isinstance(exc, httpx.HTTPError):
        return "relay_http_error"
    if isinstance(exc, ValueError):
        return "invalid_relay_request"
    return "relay_internal_error"


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))
