import time
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse

from kiapi.api._settings import settings_manager
from kiapi.api.audio.speech import _live
from kiapi.api.audio.speech.router import router
from kiapi.core.job import JobStore
from kiapi.core.worker import Worker
from kiapi.core.worker._settings import WorkerSettings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    app = FastAPI()
    app.include_router(router)
    ctx = SimpleNamespace(job_store=JobStore())
    worker = Worker(WorkerSettings(ttl_sweep_interval_s=0), ctx)  # type: ignore[arg-type]
    app.state.ctx = ctx
    app.state.worker = worker
    monkeypatch.setattr(
        _live.model_registry, "resolve", lambda *args: SimpleNamespace(name="test")
    )
    monkeypatch.setattr(
        _live, "get_voice_store", lambda: SimpleNamespace(get=lambda voice: None)
    )

    @app.on_event("startup")
    async def start() -> None:
        worker.start()

    @app.on_event("shutdown")
    async def stop() -> None:
        worker._task.cancel()  # type: ignore[union-attr]
        worker.executor.shutdown(wait=True)

    with TestClient(app) as c:
        yield c, ctx, worker


def fake_generation(ctx: Any, req: Any, source: Any, job: Any, emit: Any) -> Any:
    emit({"type": "ready", "required_prefix_tokens": 2})
    while not source.closed:
        with source.condition:
            if source.cancelled:
                raise InterruptedError()
            source.condition.wait(timeout=0.01)
    if not source.text.strip():
        raise ValueError("No target text")
    emit(b"\x01\x00" * 8)
    return {"duration_s": 0.001}, []


def test_stream_protocol(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_live, "handle_live_speech", fake_generation)
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        ws.send_json({"type": "start", "voice": "voice_test", "language": "ja"})
        assert ws.receive_json()["type"] == "session.created"
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "text.append", "text": "こんにちは。"})
        ws.send_json({"type": "text.done"})
        assert ws.receive_bytes() == b"\x01\x00" * 8
        assert ws.receive_json()["type"] == "done"


@pytest.mark.parametrize(
    "message",
    [{"type": "cancel"}, {"type": "text.append", "text": 1}, {"type": "text.done"}],
)
def test_cancel_and_invalid_input(
    client: Any, monkeypatch: pytest.MonkeyPatch, message: dict
) -> None:
    monkeypatch.setattr(_live, "handle_live_speech", fake_generation)
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        ws.send_json({"type": "start", "voice": "voice_test"})
        assert ws.receive_json()["type"] == "session.created"
        ws.send_json(message)
        events = []
        while True:
            event = ws.receive_json()
            events.append(event["type"])
            if event["type"] != "ready":
                break
        assert events[-1] == ("canceled" if message["type"] == "cancel" else "error")


def _wait() -> bool:
    time.sleep(0.15)
    return True


def test_queued_cancel_never_enters_model(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    blocker = client[1].job_store.create(type="speech", params={})
    client[0].portal.call(client[2].submit, blocker, lambda: ({"wait": _wait()}, []))
    monkeypatch.setattr(
        _live, "handle_live_speech", lambda *args: pytest.fail("Canceled job ran")
    )
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        ws.send_json({"type": "start", "voice": "voice_test"})
        ws.receive_json()
        ws.send_json({"type": "cancel"})
        assert ws.receive_json()["type"] == "canceled"
    client[0].portal.call(asyncio.sleep, 0.2)


def test_auth(client: Any) -> None:
    old = settings_manager.user_config
    settings_manager.user_config = {"auth_token": "correct"}
    try:
        with pytest.raises(WebSocketDenialResponse):
            with client[0].websocket_connect("/v1/audio/speech/stream"):
                pass
        with client[0].websocket_connect(
            "/v1/audio/speech/stream", headers={"Authorization": "Bearer correct"}
        ) as ws:
            ws.send_json({"type": "bad"})
            assert ws.receive_json()["type"] == "error"
    finally:
        settings_manager.user_config = old


def test_backpressure_cancel_releases_worker(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    finished = threading.Event()

    def flood(ctx: Any, req: Any, source: Any, job: Any, emit: Any) -> Any:
        try:
            emit({"type": "ready", "required_prefix_tokens": 1})
            while True:
                emit(b"\0" * 64)
        finally:
            finished.set()

    monkeypatch.setattr(_live, "handle_live_speech", flood)
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        ws.send_json({"type": "start", "voice": "voice_test"})
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "cancel"})
        while True:
            event = ws.receive()
            if event.get("text"):
                assert '"canceled"' in event["text"]
                break
    assert finished.wait(timeout=1)


@pytest.mark.asyncio
async def test_cancel_releases_inference_while_socket_write_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio
    import threading

    from kiapi.core.job import JobCanceledError

    inputs: asyncio.Queue[dict] = asyncio.Queue()
    writer_blocked = asyncio.Event()
    finished = threading.Event()

    class Socket:
        async def accept(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def receive_json(self) -> dict:
            return await inputs.get()

        async def send_json(self, event: dict) -> None:
            pass

        async def send_bytes(self, chunk: bytes) -> None:
            writer_blocked.set()
            await asyncio.Event().wait()

    def flood(ctx: Any, req: Any, source: Any, job: Any, emit: Any) -> Any:
        try:
            while True:
                emit(b"x")
        except JobCanceledError:
            raise
        finally:
            finished.set()

    monkeypatch.setattr(
        _live.model_registry, "resolve", lambda *args: SimpleNamespace(name="test")
    )
    monkeypatch.setattr(
        _live, "get_voice_store", lambda: SimpleNamespace(get=lambda voice: None)
    )
    monkeypatch.setattr(_live, "handle_live_speech", flood)
    ctx = SimpleNamespace(job_store=JobStore())
    worker = Worker(WorkerSettings(ttl_sweep_interval_s=0), ctx)  # type: ignore[arg-type]
    worker.start()
    task = asyncio.create_task(_live.stream_speech(Socket(), ctx, worker))  # type: ignore[arg-type]
    try:
        await inputs.put({"type": "start", "voice": "voice_test"})
        await asyncio.wait_for(writer_blocked.wait(), 1)
        await inputs.put({"type": "cancel"})
        assert await asyncio.to_thread(finished.wait, 1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        worker._task.cancel()  # type: ignore[union-attr]
        worker.executor.shutdown(wait=True)
