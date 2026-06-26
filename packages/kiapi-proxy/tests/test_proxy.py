import base64
from pathlib import Path
from typing import Any

from kiapi_relay import (
    RelayError,
    RelayFileBody,
    RelayJsonBody,
    RelayRequestError,
    RelayResponse,
)


def _json_response(value: Any, *, status: int = 200) -> RelayResponse:
    return RelayResponse(
        status=status,
        headers={"content-type": "application/json"},
        body=RelayJsonBody(value=value),
    )


def test_get_json_response(make_client: Any) -> None:
    client, fake = make_client(_json_response({"status": "ok"}))
    with client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake.received is not None
    assert fake.received.method == "GET"
    assert fake.received.path == "/health"
    assert fake.received.body is None


def test_query_string_is_forwarded(make_client: Any) -> None:
    client, fake = make_client(_json_response({"ok": True}))
    with client:
        client.get("/v1/web/fetch", params={"url": "https://example.com"})

    assert fake.received is not None
    assert fake.received.path == "/v1/web/fetch?url=https%3A%2F%2Fexample.com"


def test_post_json_body_is_forwarded(make_client: Any) -> None:
    client, fake = make_client(_json_response({"echo": True}))
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    with client:
        response = client.post("/v1/chat/completions", json=payload)

    assert response.status_code == 200
    assert fake.received is not None
    assert fake.received.method == "POST"
    assert fake.received.body == payload
    assert fake.received.multipart is None


def test_multipart_upload_is_forwarded(make_client: Any) -> None:
    client, fake = make_client(_json_response({"file_id": "f1"}))
    with client:
        response = client.post(
            "/v1/files",
            files={"file": ("a.txt", b"hello", "text/plain")},
        )

    assert response.status_code == 200
    assert fake.received is not None
    assert fake.received.multipart is not None
    assert fake.received.body is None
    files = fake.received.multipart.files
    assert len(files) == 1
    assert files[0].filename == "a.txt"
    assert files[0].content_type == "text/plain"
    assert base64.b64decode(files[0].content_base64) == b"hello"


def test_event_stream_response_is_reemitted(make_client: Any) -> None:
    relay_response = RelayResponse(
        status=200,
        headers={"content-type": "text/event-stream"},
        body=RelayJsonBody(value=[{"delta": "a"}, {"delta": "b"}, "[DONE]"]),
    )
    client, _ = make_client(relay_response)
    with client:
        response = client.post("/v1/chat/completions", json={"stream": True})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert 'data: {"delta": "a"}\n\n' in body
    assert 'data: {"delta": "b"}\n\n' in body
    assert "data: [DONE]\n\n" in body


def test_file_response_is_streamed_and_temp_file_removed(
    make_client: Any, tmp_path: Path
) -> None:
    payload = b"\x89PNG\r\n\x1a\n binary body"
    temp_file = tmp_path / "relay-body.bin"
    temp_file.write_bytes(payload)

    relay_response = RelayResponse(
        status=200,
        headers={
            "content-type": "image/png",
            "content-disposition": 'attachment; filename="out.png"',
            "x-kiapi-file-id": "file-123",
        },
        body=RelayFileBody(
            path=temp_file,
            content_type="image/png",
            size=len(payload),
        ),
    )
    client, _ = make_client(relay_response)
    with client:
        response = client.get("/v1/files/file-123/download")

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-kiapi-file-id"] == "file-123"
    assert response.headers["content-disposition"] == 'attachment; filename="out.png"'
    # The temporary relay body file is removed after the response is sent.
    assert not temp_file.exists()


def test_relay_request_error_maps_to_502(make_client: Any) -> None:
    client, fake = make_client(_json_response({}))

    async def failing_request(request: Any, *, timeout_s: float = 1800.0) -> Any:
        raise RelayRequestError(
            RelayError(code="relay_http_error", message="boom", retryable=False)
        )

    fake.request = failing_request
    with client:
        response = client.post("/v1/chat/completions", json={})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "relay_http_error"


def test_empty_body_response(make_client: Any) -> None:
    client, _ = make_client(RelayResponse(status=204, headers={}, body=None))
    with client:
        response = client.delete("/v1/files/file-1")

    assert response.status_code == 204
    assert response.content == b""
