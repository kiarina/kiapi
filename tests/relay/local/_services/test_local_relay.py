import asyncio
import json
from pathlib import Path

from kiapi.core.relay import RelayFileBody, RelayJsonBody, RelayRequest, RelayResponse
from kiapi.relay.local import LocalRelay, LocalRelaySettings
from kiapi.relay.local._schemas.local_relay_notification import LocalRelayNotification


def _relay(tmp_path: Path) -> LocalRelay:
    return LocalRelay(
        LocalRelaySettings(
            node_id="worker",
            root=tmp_path,
            prefix="private/kiapi",
            poll_interval_s=0.01,
        )
    )


def _write_request(
    relay: LocalRelay,
    session_id: str = "session-1",
    source_node_id: str = "requester",
) -> None:
    relay._session_dir(session_id).mkdir(parents=True, exist_ok=True)
    relay._request_path(session_id).write_text(
        RelayRequest(
            method="POST", path="/v1/test", body={"ok": True}
        ).model_dump_json()
    )
    relay._requests_dir().mkdir(parents=True, exist_ok=True)
    relay._request_notification_path(session_id).write_text(
        LocalRelayNotification(
            session_id=session_id,
            source_node_id=source_node_id,
        ).model_dump_json()
    )


def test_write_json_response_uses_response_json_only(tmp_path: Path) -> None:
    relay = _relay(tmp_path)
    relay._session_dir("session-1").mkdir(parents=True)

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
    assert relay._response_json_path("session-1").exists()
    assert not relay._response_body_path("session-1").exists()


def test_write_binary_response_copies_body_before_metadata(tmp_path: Path) -> None:
    relay = _relay(tmp_path)
    relay._session_dir("session-1").mkdir(parents=True)
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

    assert relay._response_body_path("session-1").read_bytes() == b"image"
    metadata = json.loads(relay._response_json_path("session-1").read_bytes())
    assert metadata["content_type"] == "image/png"
    assert metadata["size"] == 5


async def test_scan_requests_queues_once_and_reports_queued(tmp_path: Path) -> None:
    relay = _relay(tmp_path)
    _write_request(relay)

    await relay._scan_requests()
    await relay._scan_requests()

    assert relay._queue.qsize() == 1
    response = json.loads(
        (relay._responses_dir("requester") / "session-1.json").read_bytes()
    )
    assert response["status"] == "queued"


async def test_watch_recovers_completed_response_without_dispatch(
    tmp_path: Path,
) -> None:
    relay = _relay(tmp_path)
    _write_request(relay)
    relay._write_response(
        "session-1",
        RelayResponse(
            status=200,
            headers={"content-type": "application/json"},
            body=RelayJsonBody(value={"ok": True}),
        ),
    )
    await relay._scan_requests()

    async def consume() -> None:
        async for _delivery in relay.watch():
            raise AssertionError("completed response should not be yielded")

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert not relay._request_notification_path("session-1").exists()
    response = json.loads(
        (relay._responses_dir("requester") / "session-1.json").read_bytes()
    )
    assert response["status"] == "succeeded"
    assert response["response"] == {
        "content_type": "application/json",
        "size": len(b'{"ok":true}'),
    }


async def test_complete_recovers_existing_response_json(tmp_path: Path) -> None:
    relay = _relay(tmp_path)
    _write_request(relay)
    notification = LocalRelayNotification(
        session_id="session-1",
        source_node_id="requester",
    )
    relay._write_response(
        "session-1",
        RelayResponse(
            status=200,
            headers={"content-type": "application/json"},
            body=RelayJsonBody(value={"winner": True}),
        ),
    )

    await relay.complete(
        notification,
        RelayResponse(
            status=200,
            headers={"content-type": "application/json"},
            body=RelayJsonBody(value={"winner": False}),
        ),
    )

    response = json.loads(
        (relay._responses_dir("requester") / "session-1.json").read_bytes()
    )
    assert response["status"] == "succeeded"
    assert response["response"] == {
        "content_type": "application/json",
        "size": len(b'{"winner":true}'),
    }
