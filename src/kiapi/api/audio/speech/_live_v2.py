import asyncio
import concurrent.futures
import struct
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from kiapi.capabilities.speech import (
    SpeechRequest,
    prepare_call,
    run_call_utterance,
    settings_manager,
    validate_speech,
)
from kiapi.capabilities.speech.live import TextSource
from kiapi.core.app import AppContext
from kiapi.core.job import JobCanceledError
from kiapi.core.worker import Worker


async def stream_call(
    socket: WebSocket, ctx: AppContext, worker: Worker, start: dict[str, Any]
) -> None:
    loop = asyncio.get_running_loop()
    messages: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
    output: asyncio.Queue[tuple[int, bytes]] = asyncio.Queue(maxsize=8)
    state: dict[str, Any] = {}
    turn: dict[str, Any] | None = None
    seen: set[int] = set()
    preparation = None
    prep_job = None
    receiver = None
    ready = False
    message: asyncio.Task | None = None
    chunk: asyncio.Task | None = None
    pending: set[asyncio.Future] = set()

    def cancel_turn() -> None:
        if turn is not None:
            turn["canceling"] = True
            turn["source"].cancel()
            if turn.get("job") is not None:
                turn["job"].request_cancel()

    def observe(future: asyncio.Future) -> None:
        pending.add(future)

        def done(value: asyncio.Future) -> None:
            pending.discard(value)
            if not value.cancelled():
                value.exception()

        future.add_done_callback(done)

    async def receive() -> None:
        try:
            while True:
                item = await socket.receive_json()
                if not isinstance(item, dict):
                    raise ValueError("Expected JSON object")
                # Feed running turns directly so PCM network backpressure cannot
                # prevent reading a later cancel behind many text fragments.
                if (
                    turn is not None
                    and turn.get("future") is not None
                    and item.get("utterance_id") == turn["id"]
                ):
                    if item.get("type") == "text.append":
                        text = item.get("text")
                        if not isinstance(text, str):
                            raise ValueError("text must be a string")
                        if not turn.get("canceling"):
                            turn["source"].push(text)
                        continue
                    if item.get("type") == "text.done":
                        if turn.get("canceling"):
                            continue
                        if turn["source"].closed:
                            raise ValueError("text.done already received")
                        if not turn.get("canceling"):
                            turn["source"].close()
                        continue
                if item.get("type") == "session.close" or (
                    item.get("type") == "cancel"
                    and turn is not None
                    and item.get("utterance_id") == turn["id"]
                ):
                    cancel_turn()
                await messages.put(item)
        finally:
            cancel_turn()

    async def submit_turn() -> None:
        if turn is None or turn.get("future") is not None or not ready:
            return
        current = turn
        source = current["source"]
        job = ctx.job_store.create(
            type="speech",
            params={
                "protocol": 2,
                "utterance_id": current["id"],
                "voice": state["voice"],
            },
        )
        current["job"] = job

        def emit(pcm: bytes) -> None:
            if source.is_cancelled():
                raise JobCanceledError()
            queued = asyncio.run_coroutine_threadsafe(
                output.put((current["id"], pcm)), loop
            )
            while True:
                try:
                    queued.result(timeout=0.1)
                    return
                except concurrent.futures.TimeoutError:
                    if source.is_cancelled():
                        queued.cancel()
                        raise JobCanceledError() from None

        current["future"] = await worker.submit(
            job, lambda: run_call_utterance(ctx, state, source, job, emit)
        )
        observe(current["future"])

    try:
        if set(start) - {"model", "voice", "language", "seed"}:
            raise ValueError("Unknown start fields")
        req = SpeechRequest(input=" ", **start)
        validate_speech(req)
        prep_job = ctx.job_store.create(
            type="speech",
            params={"protocol": 2, "voice": req.voice, "phase": "prepare"},
        )
        await socket.send_json(
            {
                "type": "session.created",
                "protocol": 2,
                "job_id": prep_job.id,
                "sample_rate": 24000,
                "channels": 1,
                "format": "pcm_s16le",
            }
        )
        receiver = asyncio.create_task(receive())
        preparation = await worker.submit(
            prep_job, lambda: prepare_call(ctx, req, state)
        )
        observe(preparation)
        while True:
            message = asyncio.create_task(messages.get())
            chunk = asyncio.create_task(output.get())
            waits: set[asyncio.Future] = {message, chunk, receiver}
            if not ready:
                waits.add(preparation)
            future = turn.get("future") if turn else None
            if future is not None:
                waits.add(future)
            completed, _ = await asyncio.wait(
                waits, return_when=asyncio.FIRST_COMPLETED
            )
            if receiver in completed:
                message.cancel()
                chunk.cancel()
                await receiver
                return
            if preparation in completed and not ready:
                await preparation
                ready = True
                await socket.send_json({"type": "ready", "required_prefix_tokens": 1})
                if turn is not None and turn["source"].text:
                    await submit_turn()
            if message in completed:
                item = message.result()
                kind = item.get("type")
                if kind == "session.close":
                    cancel_turn()
                    return
                identifier = item.get("utterance_id")
                if (
                    isinstance(identifier, bool)
                    or not isinstance(identifier, int)
                    or not 0 < identifier <= 0xFFFFFFFF
                ):
                    raise ValueError("utterance_id must be a positive uint32")
                if kind == "utterance.start":
                    if turn is not None or identifier in seen:
                        raise ValueError(
                            "Utterances must be serialized with unique IDs"
                        )
                    seen.add(identifier)
                    turn = {
                        "id": identifier,
                        "source": TextSource(
                            max_chars=settings_manager.get_settings().max_input_chars
                        ),
                        "future": None,
                        "job": None,
                    }
                elif kind in {"text.append", "text.done", "cancel"} and (
                    turn is None or turn["id"] != identifier
                ):
                    if identifier not in seen:
                        raise ValueError("Unknown utterance_id")
                elif kind in {"text.append", "text.done", "cancel"}:
                    assert turn is not None
                    source = turn["source"]
                    if kind == "cancel":
                        cancel_turn()
                        stopped = turn.get("future")
                        if stopped is not None:
                            if turn["job"].started_at is None:
                                stopped.cancel()
                            else:
                                try:
                                    await asyncio.shield(stopped)
                                except (asyncio.CancelledError, Exception):
                                    pass
                        turn = None
                        await socket.send_json(
                            {"type": "utterance.canceled", "utterance_id": identifier}
                        )
                    elif turn.get("canceling"):
                        pass
                    elif kind == "text.append":
                        text = item.get("text")
                        if not isinstance(text, str):
                            raise ValueError("text must be a string")
                        source.push(text)
                        if text:
                            await submit_turn()
                    else:
                        if source.closed:
                            raise ValueError("text.done already received")
                        source.close()
                        if not source.text.strip():
                            cancel_turn()
                            turn = None
                            await socket.send_json(
                                {
                                    "type": "utterance.done",
                                    "utterance_id": identifier,
                                    "duration_s": 0,
                                }
                            )
                else:
                    raise ValueError("Unknown message type")
            else:
                message.cancel()
            if chunk in completed:
                identifier, pcm = chunk.result()
                if (
                    turn is not None
                    and identifier == turn["id"]
                    and not turn["source"].is_cancelled()
                ):
                    await asyncio.wait_for(
                        socket.send_bytes(struct.pack("<I", identifier) + pcm), 30
                    )
            else:
                chunk.cancel()
            future = turn.get("future") if turn else None
            if (
                turn is not None
                and future is not None
                and future.done()
                and output.empty()
            ):
                identifier = turn["id"]
                if future.cancelled():
                    event = {"type": "utterance.canceled", "utterance_id": identifier}
                else:
                    event = {
                        "type": "utterance.done",
                        "utterance_id": identifier,
                        **future.result(),
                    }
                turn = None
                await socket.send_json(event)
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        try:
            await asyncio.wait_for(
                socket.send_json(
                    {
                        "type": "error",
                        "code": "speech_stream_error",
                        "message": str(exc),
                    }
                ),
                5,
            )
        except (WebSocketDisconnect, RuntimeError, TimeoutError):
            pass
    finally:
        for waiter in (message, chunk):
            if waiter is not None:
                waiter.cancel()
        cancel_turn()
        if prep_job is not None:
            prep_job.request_cancel()
        if receiver is not None:
            receiver.cancel()
