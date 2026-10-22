# ruff: noqa: F811
import struct
import threading
from typing import Any

import pytest

from kiapi.api.audio.speech import _live_v2
from kiapi.core.job import JobCanceledError

from .test_live import client  # noqa: F401


def prepare(ctx: Any, req: Any, state: dict) -> Any:
    state.update(voice=req.voice, seed=req.seed)
    return {"required_prefix_tokens": 1}, []


def generate(ctx: Any, state: Any, source: Any, job: Any, emit: Any) -> Any:
    while not source.closed:
        with source.condition:
            if source.cancelled:
                raise JobCanceledError()
            source.condition.wait(0.01)
    if source.cancelled:
        raise JobCanceledError()
    emit(b"\x01\x00" * 16)
    return {"duration_s": 16 / 24000}, []


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_live_v2, "prepare_call", prepare)
    monkeypatch.setattr(_live_v2, "run_call_utterance", generate)


def start(ws: Any) -> None:
    ws.send_json({"type": "start", "protocol": 2, "voice": "voice_test", "seed": 42})
    assert ws.receive_json()["protocol"] == 2
    assert ws.receive_json() == {"type": "ready", "required_prefix_tokens": 1}


def utterance(ws: Any, identifier: int) -> bytes:
    ws.send_json({"type": "utterance.start", "utterance_id": identifier})
    ws.send_json(
        {"type": "text.append", "utterance_id": identifier, "text": "こんにちは。"}
    )
    ws.send_json({"type": "text.done", "utterance_id": identifier})
    pcm = ws.receive_bytes()
    assert struct.unpack("<I", pcm[:4])[0] == identifier
    event = ws.receive_json()
    assert event["type"] == "utterance.done" and event["utterance_id"] == identifier
    return bytes(pcm[4:])


def test_two_turns_one_socket_and_idle_worker(client: Any) -> None:
    async def other_job() -> Any:
        job = client[1].job_store.create(type="speech", params={})
        future = await client[2].submit(job, lambda: ({"other": True}, []))
        return await future

    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        start(ws)
        assert client[0].portal.call(other_job) == {"other": True}
        first = utterance(ws, 1)
        assert client[0].portal.call(other_job) == {"other": True}
        assert utterance(ws, 2) == first
        ws.send_json({"type": "session.close"})


def test_cancel_before_text_and_stale_messages(client: Any) -> None:
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        start(ws)
        ws.send_json({"type": "utterance.start", "utterance_id": 1})
        ws.send_json({"type": "cancel", "utterance_id": 1})
        assert ws.receive_json() == {"type": "utterance.canceled", "utterance_id": 1}
        ws.send_json({"type": "text.append", "utterance_id": 1, "text": "stale"})
        utterance(ws, 2)


def test_queued_cancel_and_next_turn(client: Any) -> None:
    gate = threading.Event()

    def block() -> Any:
        gate.wait(2)
        return {}, []

    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        start(ws)
        job = client[1].job_store.create(type="speech", params={})
        client[0].portal.call(client[2].submit, job, block)
        ws.send_json({"type": "utterance.start", "utterance_id": 1})
        ws.send_json({"type": "text.append", "utterance_id": 1, "text": "あ"})
        ws.send_json({"type": "cancel", "utterance_id": 1})
        assert ws.receive_json() == {"type": "utterance.canceled", "utterance_id": 1}
        gate.set()
        utterance(ws, 2)


def test_running_cancel_and_empty_done(client: Any) -> None:
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        start(ws)
        ws.send_json({"type": "utterance.start", "utterance_id": 1})
        ws.send_json({"type": "text.append", "utterance_id": 1, "text": "あ"})
        ws.send_json({"type": "cancel", "utterance_id": 1})
        assert ws.receive_json()["type"] == "utterance.canceled"
        ws.send_json({"type": "utterance.start", "utterance_id": 2})
        ws.send_json({"type": "text.done", "utterance_id": 2})
        assert ws.receive_json() == {
            "type": "utterance.done",
            "utterance_id": 2,
            "duration_s": 0,
        }
        utterance(ws, 3)


def test_cancel_during_preparation(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = threading.Event()

    def slow(ctx: Any, req: Any, state: Any) -> Any:
        gate.wait(2)
        return prepare(ctx, req, state)

    monkeypatch.setattr(_live_v2, "prepare_call", slow)
    with client[0].websocket_connect("/v1/audio/speech/stream") as ws:
        ws.send_json({"type": "start", "protocol": 2, "voice": "voice_test"})
        assert ws.receive_json()["type"] == "session.created"
        ws.send_json({"type": "utterance.start", "utterance_id": 1})
        ws.send_json({"type": "cancel", "utterance_id": 1})
        assert ws.receive_json()["type"] == "utterance.canceled"
        gate.set()
        assert ws.receive_json()["type"] == "ready"
        utterance(ws, 2)


@pytest.mark.asyncio
async def test_network_backpressure_cannot_hide_cancel_behind_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio
    from types import SimpleNamespace

    from kiapi.core.job import JobStore
    from kiapi.core.worker import Worker
    from kiapi.core.worker._settings import WorkerSettings

    inputs: asyncio.Queue[dict] = asyncio.Queue()
    blocked = asyncio.Event()
    finished = threading.Event()

    class Socket:
        async def send_json(self, event: dict) -> None:
            pass

        async def receive_json(self) -> dict:
            return await inputs.get()

        async def send_bytes(self, data: bytes) -> None:
            blocked.set()
            await asyncio.Event().wait()

    def flood(ctx: Any, state: Any, source: Any, job: Any, emit: Any) -> Any:
        try:
            while True:
                emit(b"\0\0")
        finally:
            finished.set()

    monkeypatch.setattr(_live_v2, "run_call_utterance", flood)
    ctx = SimpleNamespace(job_store=JobStore())
    worker = Worker(WorkerSettings(ttl_sweep_interval_s=0), ctx)  # type: ignore[arg-type]
    worker.start()
    task = asyncio.create_task(
        _live_v2.stream_call(Socket(), ctx, worker, {"voice": "voice_test"})  # type: ignore[arg-type]
    )
    try:
        await inputs.put({"type": "utterance.start", "utterance_id": 1})
        await inputs.put({"type": "text.append", "utterance_id": 1, "text": "あ"})
        await asyncio.wait_for(blocked.wait(), 1)
        for _ in range(64):
            await inputs.put({"type": "text.append", "utterance_id": 1, "text": "い"})
        await inputs.put({"type": "cancel", "utterance_id": 1})
        assert await asyncio.to_thread(finished.wait, 1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        worker._task.cancel()  # type: ignore[union-attr]
        worker.executor.shutdown(wait=True)
