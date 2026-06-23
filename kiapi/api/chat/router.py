"""Chat API: OpenAI-compatible ``POST /v1/chat/completions``.

Internally still a job (so it shows up in /v1/jobs and shares the single-flight
worker). Non-streaming callers wait for the completion dict. Streaming callers
receive OpenAI-style SSE chunks while the worker thread generates; the final job
result remains inspectable through /v1/jobs.
"""

import asyncio
import base64
import binascii
import json
import logging
import re
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from kiapi.api import (
    REQUIRE_AUTH,
    get_ctx,
    get_worker,
    register_capability_endpoints,
)
from kiapi.api._settings import settings_manager
from kiapi.capabilities.chat import ChatRequest, handle_chat
from kiapi.core.app import AppContext
from kiapi.core.memory import MemoryBudgetError
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.setup import SetupRequiredError
from kiapi.core.worker import Worker

from ._views.chat_completion_response import ChatCompletionResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=REQUIRE_AUTH)

_BASE64_PLACEHOLDER = "<base64_encoded_data>"

_DATA_URL_BASE64 = re.compile(
    r"^(?P<prefix>data:[^,]*;base64,)(?P<data>.*)$",
    re.DOTALL,
)


@router.post(
    "/v1/chat/completions",
    response_model=None,
    responses={
        200: {
            "model": ChatCompletionResponse,
            "description": (
                "Non-streaming: the full `chat.completion` object. "
                "Streaming (`stream: true`): an OpenAI `text/event-stream` of "
                "`chat.completion.chunk` events, each `data: {...}`, terminated "
                "by `data: [DONE]`. Tool calls arrive as `delta.tool_calls`; the "
                "final chunk carries `finish_reason`."
            ),
            "content": {
                "text/event-stream": {"schema": {"type": "string", "format": "binary"}},
            },
        },
        400: {"description": "Invalid request, unknown model, or bad input/modality."},
        503: {"description": "Model not set up, or memory budget exceeded."},
        504: {"description": "Sync timeout exceeded; the job keeps running."},
    },
)
async def chat_completions(
    req: ChatRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> dict | StreamingResponse:
    """Generate a chat completion (OpenAI-compatible).

    Accepts the OpenAI `chat.completions` request shape with multimodal
    `messages` (text / image / audio / video), function `tools`, and
    `tool_choice`. The resolved `model` (see GET /v1/models) determines which
    input modalities are accepted.

    Every request runs as a single-flight job, so it appears in /v1/jobs and is
    serialized with all other generation. Non-streaming callers wait up to the
    sync timeout and receive the full `chat.completion`; on timeout the job
    keeps running and can be polled at /v1/jobs/{id}. Set `stream: true` to
    receive incremental `chat.completion.chunk` SSE events instead.
    """
    settings = settings_manager.get_settings()

    logger.debug(
        "chat/completions request validated: %s",
        _redacted_chat_request_dump(req),
    )

    if req.stream:
        try:
            model_registry.resolve("chat", req.model)
        except UnknownModelError as exc:
            raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def emit(chunk: dict) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, chunk)

        def finish_stream() -> None:
            loop.call_soon_threadsafe(queue.put_nowait, None)

        def thunk():  # type: ignore
            try:
                return handle_chat(ctx, req, emit=emit)
            finally:
                finish_stream()

        job = ctx.job_store.create(
            type="chat", params={"model": req.model, "stream": True}
        )
        fut = await worker.submit(job, thunk)

        async def events() -> AsyncIterator[str]:
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield _sse(item)

                try:
                    await asyncio.shield(fut)
                except Exception as exc:
                    yield _sse(_stream_error(exc))
                yield _sse("[DONE]")
            except asyncio.CancelledError:
                # The running worker job is not preemptible; let it finish and
                # keep its final state in the job store.
                return

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    job = ctx.job_store.create(type="chat", params={"model": req.model})
    fut = await worker.submit(job, lambda: handle_chat(ctx, req))

    try:
        return await asyncio.wait_for(fut, timeout=settings.sync_timeout_s)
    except TimeoutError:
        raise HTTPException(  # noqa: B904
            status_code=504,
            detail=f"chat job {job.id} exceeded sync timeout "
            f"({settings.sync_timeout_s}s); it keeps running — poll /v1/jobs/{job.id}",
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except SetupRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except MemoryBudgetError as exc:
        raise HTTPException(status_code=503, detail=str(exc))  # noqa: B904
    except Exception as exc:
        # MediaError/CapabilityError (bad input / unsupported modality) → 400.
        if exc.__class__.__name__ in ("MediaError", "CapabilityError"):
            raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
        raise HTTPException(status_code=500, detail=f"generation failed: {exc}")  # noqa: B904


register_capability_endpoints(router, name="chat", base_path="/v1/chat")


def _redact_data_url(value: str) -> str:
    m = _DATA_URL_BASE64.match(value)
    if not m:
        return value
    return f"{m.group('prefix')}{_BASE64_PLACEHOLDER}"


def _looks_like_base64(value: str) -> bool:
    """Heuristic for bare media payloads; avoids redacting ordinary short text."""
    s = value.strip()
    if len(s) < 128:
        return False
    try:
        base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        return False
    return True


def _redact_media_source(value: Any, *, bare_base64: bool = False) -> Any:
    if not isinstance(value, str):
        return value
    redacted = _redact_data_url(value)
    if redacted != value:
        return redacted
    if bare_base64 and _looks_like_base64(value):
        return _BASE64_PLACEHOLDER
    return value


def _redact_content_part(part: Any) -> Any:
    if not isinstance(part, dict):
        return part

    out = deepcopy(part)
    for key in ("image_url", "audio_url", "video_url"):
        container = out.get(key)
        if isinstance(container, dict) and "url" in container:
            container["url"] = _redact_media_source(container["url"])
        elif isinstance(container, str):
            out[key] = _redact_media_source(container)

    for key in ("input_audio", "input_video"):
        container = out.get(key)
        if isinstance(container, dict) and "data" in container:
            container["data"] = _BASE64_PLACEHOLDER
        elif isinstance(container, str):
            out[key] = _redact_media_source(container, bare_base64=True)

    for key in ("image", "audio", "video"):
        if key in out:
            out[key] = _redact_media_source(out[key], bare_base64=True)

    return out


def _redacted_chat_request_dump(req: ChatRequest) -> str:
    data = req.model_dump(mode="json")
    messages = data.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if isinstance(content, list):
                msg["content"] = [_redact_content_part(part) for part in content]
    return json.dumps(data, ensure_ascii=False, indent=2)


def _sse(payload) -> str:  # type: ignore
    if payload == "[DONE]":
        return "data: [DONE]\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_error(exc: BaseException) -> dict:
    return {"error": {"message": str(exc), "type": exc.__class__.__name__}}
