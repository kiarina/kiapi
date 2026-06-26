import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from google.api_core.exceptions import PreconditionFailed
from google.auth.credentials import with_scopes_if_required
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.cloud import storage  # type: ignore[import-untyped]
from kiarina.lib.google import Credentials, get_credentials
from kiarina.lib.google import settings_manager as google_settings_manager

from kiapi_relay import (
    RelayDelivery,
    RelayError,
    RelayFileBody,
    RelayJsonBody,
    RelayRequest,
    RelayRequestError,
    RelayResponse,
    build_relay_response,
    new_relay_session_id,
)

from .._schemas.gcp_relay_notification import GCPRelayNotification
from .._settings import GCPRelaySettings
from .gcp_relay_delivery import GCPRelayDelivery

logger = logging.getLogger(__name__)

_GCP_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/firebase.database",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GCPRelay:
    def __init__(self, settings: GCPRelaySettings) -> None:
        self.settings = settings
        google_settings = google_settings_manager.get_settings(
            settings.google_settings_key
        )
        credentials = get_credentials(
            settings=google_settings,
            scopes=_GCP_SCOPES,
        )
        self._credentials: Credentials = with_scopes_if_required(
            credentials,
            _GCP_SCOPES,
        )
        self._storage_client = storage.Client(
            project=google_settings.project_id,
            credentials=self._credentials,
        )
        self._bucket = self._storage_client.bucket(settings.bucket)
        self._queue: asyncio.Queue[GCPRelayNotification] = asyncio.Queue()
        self._scheduled: set[str] = set()
        self._http: httpx.AsyncClient

    async def watch(self) -> AsyncIterator[RelayDelivery]:
        if self.settings.manage_bucket_lifecycle:
            await asyncio.to_thread(self._ensure_bucket_lifecycle)
        self._ensure_http()
        listener = asyncio.create_task(
            self._listen_forever(),
            name="kiapi-relay-gcp-listener",
        )
        try:
            while True:
                notification = await self._queue.get()
                try:
                    recovered = await asyncio.to_thread(
                        self._read_response_metadata,
                        notification.session_id,
                    )
                    if recovered is not None:
                        await self._finish_success(notification, recovered)
                        continue

                    request = await asyncio.to_thread(
                        self._read_request,
                        notification.session_id,
                    )
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

                yield GCPRelayDelivery(self, notification, request)
        finally:
            listener.cancel()
            await asyncio.gather(listener, return_exceptions=True)
            await self._http.aclose()

    async def request(
        self,
        request: RelayRequest,
        *,
        timeout_s: float = 1800.0,
    ) -> RelayResponse:
        self._ensure_http()
        session_id = new_relay_session_id()
        await asyncio.to_thread(self._upload_request, session_id, request)
        await self._put_request_notification(session_id)

        notification = await self._wait_for_response(session_id, timeout_s)
        if notification.get("status") == "failed":
            raise RelayRequestError(
                RelayError.model_validate(notification.get("error") or {})
            )
        return await asyncio.to_thread(self._read_response, session_id)

    async def aclose(self) -> None:
        if hasattr(self, "_http"):
            await self._http.aclose()
            del self._http

    def _ensure_http(self) -> None:
        if not hasattr(self, "_http"):
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
            )

    def _upload_request(self, session_id: str, request: RelayRequest) -> None:
        self._bucket.blob(self._request_object(session_id)).upload_from_string(
            request.model_dump_json().encode(),
            content_type="application/json",
        )

    async def _put_request_notification(self, session_id: str) -> None:
        url = self._rtdb_url(f"{self._requests_path()}/{session_id}")
        headers = await self._authorized_headers("PUT", url)
        response = await self._http.put(
            url,
            headers=headers,
            json={
                "session_id": session_id,
                "source_node_id": self.settings.source_node_id,
            },
        )
        response.raise_for_status()

    async def _wait_for_response(
        self,
        session_id: str,
        timeout_s: float,
    ) -> dict[str, Any]:
        path = (
            f"{self.settings.prefix}/nodes/{self.settings.source_node_id}"
            f"/responses/{session_id}"
        )
        deadline = time.monotonic() + timeout_s
        last_status: str | None = None
        while time.monotonic() < deadline:
            payload = await self._get_json(path)
            if isinstance(payload, dict):
                status = payload.get("status")
                if status in {"succeeded", "failed"}:
                    return payload
                if status != last_status:
                    logger.info("relay %s: %s", session_id, status)
                    last_status = status
            await asyncio.sleep(self.settings.request_poll_interval_s)
        raise TimeoutError(f"relay session {session_id} did not finish in {timeout_s}s")

    async def _get_json(self, path: str) -> Any:
        url = self._rtdb_url(path)
        headers = await self._authorized_headers("GET", url)
        response = await self._http.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def _read_response(self, session_id: str) -> RelayResponse:
        metadata = json.loads(
            self._bucket.blob(
                self._response_json_object(session_id)
            ).download_as_bytes()
        )
        body_blob = self._bucket.blob(self._response_body_object(session_id))
        body_bytes = body_blob.download_as_bytes() if body_blob.exists() else None
        return build_relay_response(metadata, body_bytes)

    async def mark_running(self, notification: GCPRelayNotification) -> None:
        await self._put_response(
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
        notification: GCPRelayNotification,
        response: RelayResponse,
    ) -> None:
        metadata: dict[str, Any] | None
        try:
            metadata = await asyncio.to_thread(
                self._write_response,
                notification.session_id,
                response,
            )
        except PreconditionFailed:
            metadata = await asyncio.to_thread(
                self._read_response_metadata,
                notification.session_id,
            )
            if metadata is None:
                raise
        assert metadata is not None
        await self._finish_success(notification, metadata)

    async def fail(
        self,
        notification: GCPRelayNotification,
        error: RelayError,
    ) -> None:
        try:
            await self._finish(
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
        notification: GCPRelayNotification,
        metadata: dict[str, Any],
    ) -> None:
        try:
            await self._finish(
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
                await self._listen_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("RTDB relay watch disconnected")
                await asyncio.sleep(self.settings.reconnect_delay_s)

    async def _listen_once(self) -> None:
        url = self._rtdb_url(self._requests_path())
        headers = await self._authorized_headers("GET", url)
        headers["Accept"] = "text/event-stream"

        async with self._http.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            event_name = ""
            data_lines: list[str] = []
            async for line in response.aiter_lines():
                if not line:
                    if data_lines:
                        await self._handle_event(event_name, "\n".join(data_lines))
                    event_name = ""
                    data_lines = []
                elif line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())

    async def _handle_event(self, event_name: str, raw_data: str) -> None:
        if event_name not in {"put", "patch"}:
            return
        event = json.loads(raw_data)
        path = event.get("path")
        data = event.get("data")
        if not isinstance(path, str):
            return

        if path == "/":
            if isinstance(data, dict):
                for session_id, value in data.items():
                    await self._schedule(session_id, value)
            return

        session_id = path.strip("/").split("/", 1)[0]
        if "/" not in path.strip("/"):
            await self._schedule(session_id, data)

    async def _schedule(self, session_id: str, value: Any) -> None:
        if not isinstance(value, dict) or session_id in self._scheduled:
            return
        notification = GCPRelayNotification.model_validate(value)
        if notification.session_id != session_id:
            raise ValueError(
                f"RTDB session key {session_id!r} does not match request payload"
            )

        self._scheduled.add(session_id)
        try:
            await self._put_response(
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
            self._scheduled.discard(session_id)
            raise

    async def _put_response(
        self,
        notification: GCPRelayNotification,
        payload: dict[str, Any],
    ) -> None:
        path = self._response_path(notification)
        url = self._rtdb_url(path)
        headers = await self._authorized_headers("PUT", url)
        response = await self._http.put(url, headers=headers, json=payload)
        response.raise_for_status()

    async def _finish(
        self,
        notification: GCPRelayNotification,
        payload: dict[str, Any],
    ) -> None:
        url = self._rtdb_url("")
        headers = await self._authorized_headers("PATCH", url)
        response = await self._http.patch(
            url,
            headers=headers,
            json={
                self._response_path(notification): payload,
                f"{self._requests_path()}/{notification.session_id}": None,
            },
        )
        response.raise_for_status()

    async def _authorized_headers(self, method: str, url: str) -> dict[str, str]:
        return await asyncio.to_thread(self._build_authorized_headers, method, url)

    def _build_authorized_headers(self, method: str, url: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        self._credentials.before_request(
            GoogleAuthRequest(),
            method,
            url,
            headers,
        )
        return headers

    def _read_request(self, session_id: str) -> RelayRequest:
        blob = self._bucket.blob(self._request_object(session_id))
        data = blob.download_as_bytes()
        return RelayRequest.model_validate_json(data)

    def _read_response_metadata(self, session_id: str) -> dict[str, Any] | None:
        blob = self._bucket.blob(self._response_json_object(session_id))
        if not blob.exists():
            return None
        value = json.loads(blob.download_as_bytes())
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
            self._bucket.blob(
                self._response_body_object(session_id)
            ).upload_from_filename(
                response.body.path,
                content_type=content_type,
                if_generation_match=0,
            )
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
        self._bucket.blob(self._response_json_object(session_id)).upload_from_string(
            payload,
            content_type="application/json",
            if_generation_match=0,
        )
        return metadata

    def _ensure_bucket_lifecycle(self) -> None:
        self._bucket.reload()
        session_prefix = f"{self.settings.prefix}/sessions/"
        for rule in self._bucket.lifecycle_rules:
            action = rule.get("action", {})
            condition = rule.get("condition", {})
            if (
                action.get("type") == "Delete"
                and condition.get("age") == self.settings.lifecycle_age_days
                and session_prefix in condition.get("matchesPrefix", [])
            ):
                return
        self._bucket.add_lifecycle_delete_rule(
            age=self.settings.lifecycle_age_days,
            matches_prefix=[session_prefix],
        )
        self._bucket.patch()

    def _rtdb_url(self, path: str) -> str:
        if path:
            return f"{self.settings.database_url}/{path}.json"
        return f"{self.settings.database_url}/.json"

    def _requests_path(self) -> str:
        return f"{self.settings.prefix}/nodes/{self.settings.node_id}/requests"

    def _response_path(self, notification: GCPRelayNotification) -> str:
        return (
            f"{self.settings.prefix}/nodes/{notification.source_node_id}/responses/"
            f"{notification.session_id}"
        )

    def _request_object(self, session_id: str) -> str:
        return f"{self.settings.prefix}/sessions/{session_id}/request.json"

    def _response_json_object(self, session_id: str) -> str:
        return f"{self.settings.prefix}/sessions/{session_id}/response.json"

    def _response_body_object(self, session_id: str) -> str:
        return f"{self.settings.prefix}/sessions/{session_id}/response.body"
