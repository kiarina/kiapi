from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx


@dataclass
class RelayResult:
    status: int
    headers: dict[str, str]
    content_type: str
    size: int
    json_body: Any | None = None
    body: bytes | None = None


class RelayClient:
    source_node_id: str

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        multipart: dict[str, object] | None = None,
        timeout_s: float = 1800.0,
    ) -> RelayResult:
        raise NotImplementedError

    def close(self) -> None:
        return None


class LocalRelayClient(RelayClient):
    def __init__(
        self,
        *,
        node_id: str | None = None,
        source_node_id: str | None = None,
        root: Path | None = None,
        prefix: str | None = None,
        poll_interval_s: float = 0.2,
    ) -> None:
        self.node_id = node_id or os.environ.get("KIAPI_RELAY_LOCAL_NODE_ID", "local")
        self.source_node_id = source_node_id or os.environ.get(
            "KIAPI_RELAY_SOURCE_NODE_ID", f"verify-{uuid.uuid4().hex[:8]}"
        )
        self.root = root or Path(
            os.environ.get("KIAPI_RELAY_LOCAL_ROOT", "/tmp/kiapi/relay")
        )
        self.prefix = (
            prefix or os.environ.get("KIAPI_RELAY_LOCAL_PREFIX", "kiapi")
        ).strip("/")
        self.poll_interval_s = poll_interval_s

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        multipart: dict[str, object] | None = None,
        timeout_s: float = 1800.0,
    ) -> RelayResult:
        session_id = _session_id()
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        self._request_path(session_id).write_bytes(
            _request_bytes(
                method, path, headers=headers, body=body, multipart=multipart
            )
        )
        request_dir = self._requests_dir()
        request_dir.mkdir(parents=True, exist_ok=True)
        self._request_notification_path(session_id).write_bytes(
            _json_bytes(
                {
                    "session_id": session_id,
                    "source_node_id": self.source_node_id,
                }
            )
        )

        notification = self._wait_for_terminal_notification(session_id, timeout_s)
        if notification.get("status") == "failed":
            raise RuntimeError(f"relay request failed: {notification.get('error')}")
        return self._read_result(session_id)

    def _wait_for_terminal_notification(
        self, session_id: str, timeout_s: float
    ) -> dict[str, Any]:
        path = self._response_notification_path(session_id)
        deadline = time.time() + timeout_s
        last_status = None
        while time.time() < deadline:
            if path.exists():
                payload = json.loads(path.read_bytes())
                if not isinstance(payload, dict):
                    raise RuntimeError(f"invalid relay notification: {payload!r}")
                status = payload.get("status")
                if status in {"succeeded", "failed"}:
                    return cast(dict[str, Any], payload)
                if status != last_status:
                    print(f"  relay {session_id}: {status}")
                    last_status = status
            time.sleep(self.poll_interval_s)
        raise TimeoutError(f"relay session {session_id} did not finish in {timeout_s}s")

    def _read_result(self, session_id: str) -> RelayResult:
        metadata = json.loads(self._response_json_path(session_id).read_bytes())
        body_path = self._response_body_path(session_id)
        body = body_path.read_bytes() if body_path.exists() else None
        return _result_from_metadata(metadata, body)

    def _base_dir(self) -> Path:
        return self.root.expanduser() / self.prefix

    def _session_dir(self, session_id: str) -> Path:
        return self._base_dir() / "sessions" / session_id

    def _request_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "request.json"

    def _response_json_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "response.json"

    def _response_body_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "response.body"

    def _requests_dir(self) -> Path:
        return self._base_dir() / "nodes" / self.node_id / "requests"

    def _request_notification_path(self, session_id: str) -> Path:
        return self._requests_dir() / f"{session_id}.json"

    def _response_notification_path(self, session_id: str) -> Path:
        return (
            self._base_dir()
            / "nodes"
            / self.source_node_id
            / "responses"
            / f"{session_id}.json"
        )


class GCPRelayClient(RelayClient):
    def __init__(
        self,
        *,
        node_id: str | None = None,
        source_node_id: str | None = None,
        database_url: str | None = None,
        bucket: str | None = None,
        prefix: str | None = None,
        google_settings_key: str | None = None,
        poll_interval_s: float = 0.5,
    ) -> None:
        try:
            from google.auth.credentials import with_scopes_if_required
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.cloud import storage  # type: ignore[import-untyped]
            from kiarina.lib.google import get_credentials
            from kiarina.lib.google import settings_manager as google_settings_manager
        except ImportError as exc:
            raise RuntimeError(
                "GCP relay verification requires kiapi[relay-gcp] dependencies."
            ) from exc

        scopes = [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/firebase.database",
            "https://www.googleapis.com/auth/userinfo.email",
        ]
        self.node_id = _required(
            node_id or os.environ.get("KIAPI_RELAY_GCP_NODE_ID"),
            "KIAPI_RELAY_GCP_NODE_ID",
        )
        self.source_node_id = source_node_id or os.environ.get(
            "KIAPI_RELAY_SOURCE_NODE_ID", f"verify-{uuid.uuid4().hex[:8]}"
        )
        self.database_url = _required(
            database_url or os.environ.get("KIAPI_RELAY_GCP_DATABASE_URL"),
            "KIAPI_RELAY_GCP_DATABASE_URL",
        ).rstrip("/")
        self.bucket_name = _required(
            bucket or os.environ.get("KIAPI_RELAY_GCP_BUCKET"),
            "KIAPI_RELAY_GCP_BUCKET",
        )
        self.prefix = (
            prefix or os.environ.get("KIAPI_RELAY_GCP_PREFIX", "kiapi")
        ).strip("/")
        self.poll_interval_s = poll_interval_s

        google_settings = google_settings_manager.get_settings(google_settings_key)
        self.credentials = with_scopes_if_required(
            get_credentials(settings=google_settings, scopes=scopes),
            scopes,
        )
        self.auth_request = GoogleAuthRequest()
        self.storage_client = storage.Client(
            project=google_settings.project_id,
            credentials=self.credentials,
        )
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.http = httpx.Client(timeout=httpx.Timeout(30.0, read=30.0))

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        multipart: dict[str, object] | None = None,
        timeout_s: float = 1800.0,
    ) -> RelayResult:
        session_id = _session_id()
        self.bucket.blob(self._request_object(session_id)).upload_from_string(
            _request_bytes(
                method, path, headers=headers, body=body, multipart=multipart
            ),
            content_type="application/json",
        )
        self._put_json(
            self._request_path(session_id),
            {"session_id": session_id, "source_node_id": self.source_node_id},
        )

        notification = self._wait_for_terminal_notification(session_id, timeout_s)
        if notification.get("status") == "failed":
            raise RuntimeError(f"relay request failed: {notification.get('error')}")
        return self._read_result(session_id)

    def close(self) -> None:
        self.http.close()

    def _wait_for_terminal_notification(
        self, session_id: str, timeout_s: float
    ) -> dict[str, Any]:
        path = self._response_path(session_id)
        deadline = time.time() + timeout_s
        last_status = None
        while time.time() < deadline:
            payload = self._get_json(path)
            if isinstance(payload, dict):
                status = payload.get("status")
                if status in {"succeeded", "failed"}:
                    return payload
                if status != last_status:
                    print(f"  relay {session_id}: {status}")
                    last_status = status
            time.sleep(self.poll_interval_s)
        raise TimeoutError(f"relay session {session_id} did not finish in {timeout_s}s")

    def _read_result(self, session_id: str) -> RelayResult:
        metadata = json.loads(
            self.bucket.blob(self._response_json_object(session_id)).download_as_bytes()
        )
        body_blob = self.bucket.blob(self._response_body_object(session_id))
        body = body_blob.download_as_bytes() if body_blob.exists() else None
        return _result_from_metadata(metadata, body)

    def _authorized_headers(self, method: str, url: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        self.credentials.before_request(self.auth_request, method, url, headers)
        return headers

    def _get_json(self, path: str) -> Any:
        url = self._rtdb_url(path)
        response = self.http.get(url, headers=self._authorized_headers("GET", url))
        response.raise_for_status()
        return response.json()

    def _put_json(self, path: str, value: dict[str, Any]) -> None:
        url = self._rtdb_url(path)
        response = self.http.put(
            url,
            headers=self._authorized_headers("PUT", url),
            json=value,
        )
        response.raise_for_status()

    def _rtdb_url(self, path: str) -> str:
        return f"{self.database_url}/{path}.json"

    def _request_path(self, session_id: str) -> str:
        return f"{self.prefix}/nodes/{self.node_id}/requests/{session_id}"

    def _response_path(self, session_id: str) -> str:
        return f"{self.prefix}/nodes/{self.source_node_id}/responses/{session_id}"

    def _request_object(self, session_id: str) -> str:
        return f"{self.prefix}/sessions/{session_id}/request.json"

    def _response_json_object(self, session_id: str) -> str:
        return f"{self.prefix}/sessions/{session_id}/response.json"

    def _response_body_object(self, session_id: str) -> str:
        return f"{self.prefix}/sessions/{session_id}/response.body"


def assert_json(result: RelayResult) -> Any:
    if result.json_body is None:
        raise AssertionError(f"expected JSON body, got {result.content_type}")
    return result.json_body


def data_url(path: Path, content_type: str) -> str:
    return (
        f"data:{content_type};base64,"
        f"{base64.b64encode(path.read_bytes()).decode('ascii')}"
    )


def run_checks(checks: list[tuple[str, Any]], *, fast: bool = False) -> int:
    failures: list[str] = []
    for name, fn in checks:
        started = time.time()
        try:
            detail = fn()
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


def query_path(path: str, **params: str) -> str:
    query = httpx.QueryParams(params)
    return f"{path}?{query}" if query else path


def _request_bytes(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None,
    body: dict[str, object] | None,
    multipart: dict[str, object] | None,
) -> bytes:
    if body is not None and multipart is not None:
        raise ValueError("body and multipart cannot both be set")
    return _json_bytes(
        {
            "method": method.upper(),
            "path": path,
            "headers": headers or {},
            "body": body,
            "multipart": multipart,
        }
    )


def _result_from_metadata(metadata: dict[str, Any], body: bytes | None) -> RelayResult:
    return RelayResult(
        status=int(metadata["status"]),
        headers=dict(metadata.get("headers") or {}),
        content_type=str(metadata["content_type"]),
        size=int(metadata["size"]),
        json_body=metadata.get("body"),
        body=body,
    )


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def _session_id() -> str:
    return f"session-{uuid.uuid4().hex}"


def _required(value: str | None, env_name: str) -> str:
    if not value:
        raise RuntimeError(f"{env_name} is required")
    return value
