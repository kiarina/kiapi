import asyncio
import concurrent.futures
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from kiapi.capabilities.speech import (
    SpeechRequest,
    get_voice_store,
    handle_live_speech,
    settings_manager,
    validate_speech,
)
from kiapi.capabilities.speech.live import TextSource
from kiapi.core.app import AppContext
from kiapi.core.job import JobCanceledError
from kiapi.core.model import model_registry
from kiapi.core.worker import Worker


async def stream_speech(socket: WebSocket, ctx: AppContext, worker: Worker) -> None:
    await socket.accept()
    source = TextSource(max_chars=settings_manager.get_settings().max_input_chars)
    job = None
    receiver = None
    future = None
    loop = asyncio.get_running_loop()
    output: asyncio.Queue[bytes | dict[str, Any]] = asyncio.Queue(maxsize=8)

    def emit(item: bytes | dict[str, Any]) -> None:
        if source.is_cancelled():
            raise JobCanceledError()
        pending = asyncio.run_coroutine_threadsafe(output.put(item), loop)
        while True:
            try:
                pending.result(timeout=0.1)
                return
            except concurrent.futures.TimeoutError:
                if source.is_cancelled():
                    pending.cancel()
                    raise JobCanceledError() from None

    try:
        first = await asyncio.wait_for(socket.receive_json(), timeout=30)
        if not isinstance(first, dict) or first.pop("type", None) != "start":
            raise ValueError("First message must be start")
        if set(first) - {"model", "voice", "language", "seed"}:
            raise ValueError("Unknown start fields")
        req = SpeechRequest(input=" ", **first)
        validate_speech(req)
        spec = model_registry.resolve("speech", req.model)
        get_voice_store().get(req.voice)
        job = ctx.job_store.create(
            type="speech", params={"model": spec.name, "voice": req.voice}
        )
        await socket.send_json(
            {
                "type": "session.created",
                "job_id": job.id,
                "sample_rate": 24000,
                "channels": 1,
                "format": "pcm_s16le",
            }
        )

        async def receive() -> None:
            while True:
                message = await asyncio.wait_for(
                    socket.receive_json(), timeout=None if source.closed else 30
                )
                if not isinstance(message, dict):
                    raise ValueError("Expected JSON object")
                kind = message.get("type")
                if kind == "text.append":
                    text = message.get("text")
                    if not isinstance(text, str):
                        raise ValueError("text must be a string")
                    source.push(text)
                elif kind == "text.done":
                    if source.closed:
                        raise ValueError("text.done already received")
                    source.close()
                elif kind == "cancel":
                    return
                else:
                    raise ValueError("Unknown message type")

        receiver = asyncio.create_task(receive())
        future = await worker.submit(
            job, lambda: handle_live_speech(ctx, req, source, job, emit)
        )
        while True:
            chunk = asyncio.create_task(output.get())
            completed, _ = await asyncio.wait(
                {chunk, receiver, future}, return_when=asyncio.FIRST_COMPLETED
            )
            if receiver in completed:
                chunk.cancel()
                await receiver
                source.cancel()
                job.request_cancel()
                await socket.send_json({"type": "canceled"})
                return
            if chunk in completed:
                item = chunk.result()
                if isinstance(item, bytes):
                    await asyncio.wait_for(socket.send_bytes(item), timeout=30)
                else:
                    await asyncio.wait_for(socket.send_json(item), timeout=30)
            else:
                chunk.cancel()
            if future in completed and output.empty():
                if future.cancelled():
                    await socket.send_json({"type": "canceled"})
                    return
                result = await future
                await socket.send_json({"type": "done", **result})
                return
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        try:
            await socket.send_json(
                {"type": "error", "message": str(exc), "code": "speech_stream_error"}
            )
        except (WebSocketDisconnect, RuntimeError):
            pass
    finally:
        source.cancel()
        if job is not None and (future is None or not future.done()):
            job.request_cancel()
        if receiver is not None:
            receiver.cancel()
        if future is not None:

            def consume(done: asyncio.Future) -> None:
                if not done.cancelled():
                    done.exception()

            future.add_done_callback(consume)
        try:
            await socket.close()
        except (WebSocketDisconnect, RuntimeError):
            pass
