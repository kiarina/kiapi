import asyncio
import json
from pathlib import Path
from typing import Any

from kiapi_relay import RelayFileBody, RelayJsonBody, RelayResponse
from kiapi_relay.impl.gcp import GCPRelay, GCPRelaySettings
from kiapi_relay.impl.gcp._services.gcp_relay import _GCP_SCOPES


class _Blob:
    def __init__(self, name: str, calls: list[tuple[str, str, dict[str, Any]]]) -> None:
        self.name = name
        self.calls = calls

    def upload_from_filename(self, path: Path, **kwargs: Any) -> None:
        self.calls.append(("filename", self.name, {"path": path, **kwargs}))

    def upload_from_string(self, value: bytes, **kwargs: Any) -> None:
        self.calls.append(("string", self.name, {"value": value, **kwargs}))


class _Bucket:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def blob(self, name: str) -> _Blob:
        return _Blob(name, self.calls)


def _relay() -> GCPRelay:
    relay = object.__new__(GCPRelay)
    relay.settings = GCPRelaySettings(
        database_url="https://example.firebaseio.com",
        bucket="relay-bucket",
        prefix="private/kiapi",
    )
    relay._node_id = "worker"
    relay._bucket = _Bucket()
    relay._scheduled = set()
    relay._queue = asyncio.Queue()
    return relay


def test_write_json_response_uses_response_json_only() -> None:
    relay = _relay()

    metadata = relay._write_response(
        "session-1",
        RelayResponse(
            status=200,
            headers={"content-type": "application/json"},
            body=RelayJsonBody(value={"ok": True}),
        ),
    )

    assert metadata["body"] == {"ok": True}
    assert metadata["content_type"] == "application/json"
    calls = relay._bucket.calls
    assert [call[1] for call in calls] == [
        "private/kiapi/sessions/session-1/response.json"
    ]
    assert calls[0][2]["if_generation_match"] == 0


def test_write_binary_response_uploads_body_before_metadata(tmp_path: Path) -> None:
    relay = _relay()
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"image")

    relay._write_response(
        "session-1",
        RelayResponse(
            status=200,
            body=RelayFileBody(
                path=file_path,
                content_type="image/png",
                size=5,
            ),
        ),
    )

    calls = relay._bucket.calls
    assert [call[1] for call in calls] == [
        "private/kiapi/sessions/session-1/response.body",
        "private/kiapi/sessions/session-1/response.json",
    ]
    metadata = json.loads(calls[1][2]["value"])
    assert metadata["content_type"] == "image/png"
    assert metadata["size"] == 5


async def test_put_event_queues_once_and_reports_queued() -> None:
    relay = _relay()
    reports: list[dict[str, Any]] = []

    async def put_response(notification: Any, payload: dict[str, Any]) -> None:
        reports.append(payload)

    relay._put_response = put_response  # type: ignore[method-assign]
    event = json.dumps(
        {
            "path": "/session-1",
            "data": {
                "session_id": "session-1",
                "source_node_id": "requester",
            },
        }
    )

    await relay._handle_event("put", event)
    await relay._handle_event("put", event)

    assert relay._queue.qsize() == 1
    assert reports[0]["status"] == "queued"


def test_rtdb_url_uses_firebase_root_json_path() -> None:
    relay = _relay()

    assert relay._rtdb_url("") == "https://example.firebaseio.com/.json"
    assert (
        relay._rtdb_url("private/kiapi/nodes/worker/requests")
        == "https://example.firebaseio.com/private/kiapi/nodes/worker/requests.json"
    )


def test_gcp_scopes_cover_storage_and_rtdb_rest() -> None:
    assert _GCP_SCOPES == [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/firebase.database",
        "https://www.googleapis.com/auth/userinfo.email",
    ]
