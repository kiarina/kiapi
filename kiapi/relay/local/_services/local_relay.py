import asyncio
import json
import logging
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from kiapi.core.relay import (
    RelayDelivery,
    RelayError,
    RelayFileBody,
    RelayJsonBody,
    RelayRequest,
    RelayResponse,
)

from .._schemas.local_relay_notification import LocalRelayNotification
from .._settings import LocalRelaySettings
from .local_relay_delivery import LocalRelayDelivery

logger = logging.getLogger(__name__)


class LocalRelay:
    def __init__(self, settings: LocalRelaySettings) -> None:
        self.settings = settings
        self._queue: asyncio.Queue[LocalRelayNotification] = asyncio.Queue()
        self._scheduled: set[str] = set()

    async def watch(self) -> AsyncIterator[RelayDelivery]:
        self._ensure_directories()
        listener = asyncio.create_task(
            self._listen_forever(),
            name="kiapi-relay-local-listener",
        )
        try:
            while True:
                notification = await self._queue.get()
                try:
                    recovered = self._read_response_metadata(notification.session_id)
                    if recovered is not None:
                        await self._finish_success(notification, recovered)
                        continue

                    request = self._read_request(notification.session_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    await self.fail(
                        notification,
                        RelayError(
                            code="invalid_relay_request",
                            message=str(exc) or exc.__class__.__name__,
                            retryable=False,
                        ),
                    )
                    continue

                yield LocalRelayDelivery(self, notification, request)
        finally:
            listener.cancel()
            await asyncio.gather(listener, return_exceptions=True)

    async def mark_running(self, notification: LocalRelayNotification) -> None:
        self._write_response_notification(
            notification,
            {
                "session_id": notification.session_id,
                "source_node_id": self.settings.node_id,
                "status": "running",
                "progress": {
                    "value": 0.0,
                    "message": "Relay is dispatching the API request.",
                },
            },
        )

    async def complete(
        self,
        notification: LocalRelayNotification,
        response: RelayResponse,
    ) -> None:
        try:
            metadata = self._write_response(notification.session_id, response)
        except FileExistsError:
            recovered = self._read_response_metadata(notification.session_id)
            if recovered is None:
                raise
            await self._finish_success(notification, recovered)
            return
        await self._finish_success(notification, metadata)

    async def fail(
        self,
        notification: LocalRelayNotification,
        error: RelayError,
    ) -> None:
        try:
            self._finish(
                notification,
                {
                    "session_id": notification.session_id,
                    "source_node_id": self.settings.node_id,
                    "status": "failed",
                    "error": error.model_dump(mode="json"),
                },
            )
        finally:
            self._scheduled.discard(notification.session_id)

    async def _finish_success(
        self,
        notification: LocalRelayNotification,
        metadata: dict[str, Any],
    ) -> None:
        try:
            self._finish(
                notification,
                {
                    "session_id": notification.session_id,
                    "source_node_id": self.settings.node_id,
                    "status": "succeeded",
                    "response": {
                        "content_type": metadata["content_type"],
                        "size": metadata["size"],
                    },
                },
            )
        finally:
            self._scheduled.discard(notification.session_id)

    async def _listen_forever(self) -> None:
        while True:
            try:
                await self._scan_requests()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Local relay watch scan failed")
            await asyncio.sleep(self.settings.poll_interval_s)

    async def _scan_requests(self) -> None:
        for path in sorted(self._requests_dir().glob("*.json")):
            if not path.is_file():
                continue
            session_id = path.stem
            if session_id in self._scheduled:
                continue
            notification = LocalRelayNotification.model_validate_json(path.read_bytes())
            if notification.session_id != session_id:
                raise ValueError(
                    f"request file {session_id!r} does not match notification payload"
                )
            await self._schedule(notification)

    async def _schedule(self, notification: LocalRelayNotification) -> None:
        self._scheduled.add(notification.session_id)
        try:
            self._write_response_notification(
                notification,
                {
                    "session_id": notification.session_id,
                    "source_node_id": self.settings.node_id,
                    "status": "queued",
                    "progress": {
                        "value": 0.0,
                        "message": "Relay request was queued.",
                    },
                },
            )
            self._queue.put_nowait(notification)
        except Exception:
            self._scheduled.discard(notification.session_id)
            raise

    def _read_request(self, session_id: str) -> RelayRequest:
        return RelayRequest.model_validate_json(
            self._request_path(session_id).read_bytes()
        )

    def _read_response_metadata(self, session_id: str) -> dict[str, Any] | None:
        path = self._response_json_path(session_id)
        if not path.exists():
            return None
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict):
            raise ValueError("response.json must contain a JSON object")
        content_type = value.get("content_type")
        size = value.get("size")
        if not isinstance(content_type, str) or not isinstance(size, int):
            raise ValueError("response.json recovery metadata is incomplete")
        return value

    def _write_response(
        self,
        session_id: str,
        response: RelayResponse,
    ) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        metadata: dict[str, Any] = {
            "status": response.status,
            "headers": response.headers,
        }

        if isinstance(response.body, RelayFileBody):
            content_type = response.body.content_type
            metadata.update(
                content_type=content_type,
                size=response.body.size,
            )
            shutil.copyfile(response.body.path, self._response_body_path(session_id))
        elif isinstance(response.body, RelayJsonBody):
            content_type = content_type or "application/json"
            body_bytes = json.dumps(
                response.body.value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
            metadata.update(
                content_type=content_type,
                size=len(body_bytes),
                body=response.body.value,
            )
        else:
            metadata.update(
                content_type=content_type or "application/octet-stream",
                size=0,
            )

        payload = json.dumps(
            metadata,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        with self._response_json_path(session_id).open("xb") as file:
            file.write(payload)
        return metadata

    def _write_response_notification(
        self,
        notification: LocalRelayNotification,
        payload: dict[str, Any],
    ) -> None:
        path = self._response_notification_path(notification)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(path, payload)

    def _finish(
        self,
        notification: LocalRelayNotification,
        payload: dict[str, Any],
    ) -> None:
        self._write_response_notification(notification, payload)
        self._request_notification_path(notification.session_id).unlink(missing_ok=True)

    def _ensure_directories(self) -> None:
        self._requests_dir().mkdir(parents=True, exist_ok=True)
        self._sessions_dir().mkdir(parents=True, exist_ok=True)

    def _base_dir(self) -> Path:
        return self.settings.root.expanduser() / self.settings.prefix

    def _sessions_dir(self) -> Path:
        return self._base_dir() / "sessions"

    def _session_dir(self, session_id: str) -> Path:
        return self._sessions_dir() / session_id

    def _nodes_dir(self) -> Path:
        return self._base_dir() / "nodes"

    def _requests_dir(self) -> Path:
        return self._nodes_dir() / self.settings.node_id / "requests"

    def _request_notification_path(self, session_id: str) -> Path:
        return self._requests_dir() / f"{session_id}.json"

    def _responses_dir(self, source_node_id: str) -> Path:
        return self._nodes_dir() / source_node_id / "responses"

    def _response_notification_path(
        self,
        notification: LocalRelayNotification,
    ) -> Path:
        return self._responses_dir(notification.source_node_id) / (
            f"{notification.session_id}.json"
        )

    def _request_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "request.json"

    def _response_json_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "response.json"

    def _response_body_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "response.body"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_bytes(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    )
    temporary_path.replace(path)
