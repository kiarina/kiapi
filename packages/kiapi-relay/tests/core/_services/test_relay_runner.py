import asyncio
import base64
from collections.abc import AsyncIterator

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response, StreamingResponse

from kiapi_relay import (
    RelayDelivery,
    RelayFileBody,
    RelayJsonBody,
    RelayMultipartBody,
    RelayMultipartFile,
    RelayRequest,
    RelayResponse,
    RelayRunner,
)


class _Relay:
    name = "test"
    node_id = "test-node"

    async def watch(self) -> AsyncIterator[RelayDelivery]:
        queue: asyncio.Queue[RelayDelivery] = asyncio.Queue()
        yield await queue.get()

    async def request(
        self,
        request: RelayRequest,
        *,
        timeout_s: float = 1800.0,
    ) -> RelayResponse:
        raise NotImplementedError


def _app() -> FastAPI:
    app = FastAPI()

    @app.post("/json")
    async def json_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/binary")
    async def binary_endpoint() -> Response:
        return Response(b"binary", media_type="image/png")

    @app.get("/stream")
    async def stream_endpoint() -> StreamingResponse:
        async def body() -> AsyncIterator[str]:
            yield 'data: {"value":1}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(body(), media_type="text/event-stream")

    @app.post("/upload")
    async def upload_endpoint(file: UploadFile = File()) -> dict[str, str | int | None]:
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "content": (await file.read()).decode(),
        }

    return app


class _CrashingRelay(_Relay):
    async def watch(self) -> AsyncIterator[RelayDelivery]:
        queue: asyncio.Queue[RelayDelivery] = asyncio.Queue()
        for _ in range(0):
            yield await queue.get()
        raise RuntimeError("boom")


def test_status_reports_not_running_before_start() -> None:
    runner = RelayRunner(_Relay(), _app())

    status = runner.status()

    assert status.name == "test"
    assert status.running is False
    assert status.failed is False


async def test_status_reports_running_while_watching() -> None:
    # _Relay.watch blocks forever on an empty queue, mirroring an idle relay.
    runner = RelayRunner(_Relay(), _app())
    runner.start()
    await asyncio.sleep(0)

    status = runner.status()

    assert status.running is True
    assert status.failed is False
    await runner.stop()


async def test_status_reports_failed_when_watch_loop_stops() -> None:
    runner = RelayRunner(_CrashingRelay(), _app())
    runner.start()
    assert runner._task is not None
    await asyncio.gather(runner._task, return_exceptions=True)

    status = runner.status()

    assert status.running is False
    assert status.failed is True
    await runner.stop()


async def test_dispatch_collects_json_response() -> None:
    runner = RelayRunner(_Relay(), _app())

    response, path = await runner._dispatch(
        RelayRequest(method="POST", path="/json", body={"input": "hello"})
    )

    assert response.status == 200
    assert response.body == RelayJsonBody(value={"ok": True})
    assert path is None
    await runner.stop()


async def test_dispatch_spools_binary_response() -> None:
    runner = RelayRunner(_Relay(), _app())

    response, path = await runner._dispatch(RelayRequest(method="GET", path="/binary"))

    assert isinstance(response.body, RelayFileBody)
    assert response.body.content_type == "image/png"
    assert response.body.path.read_bytes() == b"binary"
    assert path == response.body.path
    path.unlink()
    await runner.stop()


async def test_dispatch_collects_event_stream_as_json_array() -> None:
    runner = RelayRunner(_Relay(), _app())

    response, _ = await runner._dispatch(RelayRequest(method="GET", path="/stream"))

    assert response.body == RelayJsonBody(value=[{"value": 1}, "[DONE]"])
    await runner.stop()


async def test_dispatch_sends_multipart_file_upload() -> None:
    runner = RelayRunner(_Relay(), _app())

    response, path = await runner._dispatch(
        RelayRequest(
            method="POST",
            path="/upload",
            headers={"content-type": "multipart/form-data"},
            multipart=RelayMultipartBody(
                files=[
                    RelayMultipartFile(
                        field="file",
                        filename="hello.txt",
                        content_type="text/plain",
                        content_base64=base64.b64encode(b"hello").decode("ascii"),
                    )
                ],
            ),
        )
    )

    assert response.status == 200
    assert response.body == RelayJsonBody(
        value={
            "filename": "hello.txt",
            "content_type": "text/plain",
            "content": "hello",
        }
    )
    assert path is None
    await runner.stop()
