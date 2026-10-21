"""Speech API: ``POST /v1/audio/speech`` (OpenAI compatible) and ``/v1/audio/voices``."""

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse

from kiapi.api import (
    REQUIRE_AUTH,
    build_job_responses,
    get_accept,
    get_ctx,
    get_worker,
    register_capability_endpoints,
    submit_and_maybe_wait,
)
from kiapi.api.audio.transcriptions._operations.run_transcription import (
    run_transcription,
)
from kiapi.capabilities import CapabilityError, resolve_file_ref
from kiapi.capabilities.speech import (
    SpeechRequest,
    ValidationError,
    Voice,
    VoiceCreateRequest,
    VoiceList,
    VoiceNotFoundError,
    get_voice_store,
    handle_speech,
    settings_manager,
    validate_speech,
)
from kiapi.capabilities.transcription import TranscriptionRequest
from kiapi.core.app import AppContext
from kiapi.core.memory import MemoryBudgetError
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.setup import SetupRequiredError
from kiapi.core.worker import Worker

from ._views.speech_response import SpeechResponse

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=REQUIRE_AUTH)

SAMPLE_RATE = 24_000


def _speech_responses() -> dict:
    responses = build_job_responses("audio/wav", result_model=SpeechResponse)
    responses.pop(202, None)  # no async mode
    responses[200]["content"]["audio/pcm"] = {
        "schema": {"type": "string", "format": "binary"}
    }
    return responses


@router.post("/v1/audio/speech", responses=_speech_responses())
async def create_speech(
    req: SpeechRequest,
    request: Request,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Speak `input` in a registered voice (OpenAI `audio/speech` compatible).

    `voice` is the id of a voice registered with POST /v1/audio/voices; there are
    no built-in voices. With `response_format: pcm` (default) the audio streams as
    it is generated, and closing the connection stops the generation. With `wav`
    the whole file is returned when generation finishes.

    The request waits in kiapi's single worker queue while another job runs.
    """
    try:
        spec = model_registry.resolve("speech", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_speech(req)
        get_voice_store().get(req.voice)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    except VoiceNotFoundError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail=f"voice {req.voice!r} is not registered"
        )

    params = {
        "model": spec.name,
        "voice": req.voice,
        "response_format": req.response_format,
    }
    if req.response_format == "wav":
        return await submit_and_maybe_wait(
            ctx,
            worker,
            type="speech",
            params=params,
            thunk=lambda: handle_speech(ctx, req),
            mode="sync",
            accept=accept,
        )
    return await _stream_pcm(req, request, ctx, worker, params)


async def _stream_pcm(
    req: SpeechRequest,
    request: Request,
    ctx: AppContext,
    worker: Worker,
    params: dict,
) -> Response:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    def emit(chunk: bytes) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, chunk)

    def thunk():  # type: ignore
        try:
            return handle_speech(ctx, req, job=job, emit=emit)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    job = ctx.job_store.create(type="speech", params=params)
    fut = await worker.submit(job, thunk)

    # Wait for the first chunk (the job may be queued behind others) so errors
    # before any audio still get an HTTP status, and a client that leaves while
    # waiting cancels the job.
    watcher = asyncio.create_task(_cancel_on_disconnect(request, job, fut))
    try:
        first = await queue.get()
    finally:
        watcher.cancel()
    if first is None:
        try:
            await asyncio.shield(fut)
        except Exception as exc:
            raise _http_error(exc) from exc

    async def body() -> AsyncIterator[bytes]:
        try:
            item = first
            while item is not None:
                yield item
                item = await queue.get()
        except asyncio.CancelledError:
            job.request_cancel()
            raise

    return StreamingResponse(
        body(),
        media_type="audio/pcm",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Kiapi-Job-Id": job.id,
            "X-Kiapi-Sample-Rate": str(SAMPLE_RATE),
        },
    )


async def _cancel_on_disconnect(request: Request, job, fut: asyncio.Future) -> None:  # type: ignore
    while not fut.done():
        if await request.is_disconnected():
            job.request_cancel()
            return
        await asyncio.sleep(0.1)


def _http_error(exc: BaseException) -> HTTPException:
    if isinstance(exc, UnknownModelError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, SetupRequiredError | MemoryBudgetError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValidationError | CapabilityError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=f"speech failed: {exc}")


@router.post("/v1/audio/voices", response_model=Voice)
async def create_voice(
    req: VoiceCreateRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Voice:
    """Register a voice from reference audio and its transcript.

    Without `transcript`, kiapi transcribes the reference (after cutting it to
    the maximum length) with the transcription family and stores that text. The
    transcription waits in kiapi's single worker queue like any other job.
    """
    settings = settings_manager.get_settings()
    try:
        source = resolve_file_ref(ctx.file_store, req.audio, kind="audio")
        voice = await run_in_threadpool(
            get_voice_store().create,
            Path(source.path),
            name=req.name,
            transcript=req.transcript,
            min_seconds=settings.min_reference_seconds,
            max_seconds=settings.max_reference_seconds,
        )
    except CapabilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    if voice.transcript is not None or not settings.transcribe_reference:
        return voice
    return await _transcribe_reference(ctx, worker, voice)


async def _transcribe_reference(ctx: AppContext, worker: Worker, voice: Voice) -> Voice:
    store = get_voice_store()
    try:
        ctx.ensure_model_ready(model_registry.resolve("transcription", None))
    except SetupRequiredError as exc:
        logger.warning("voice %s registered without a transcript: %s", voice.id, exc)
        return voice
    try:
        result = await run_transcription(
            ctx, worker, TranscriptionRequest(), store.reference_path(voice.id)
        )
    except BaseException:
        store.delete(voice.id)
        raise
    return store.set_transcript(voice.id, result["text"])


@router.get("/v1/audio/voices", response_model=VoiceList)
async def list_voices() -> VoiceList:
    """List registered voices, oldest first."""
    return VoiceList(data=get_voice_store().list())


@router.get("/v1/audio/voices/{voice_id}", response_model=Voice)
async def get_voice(voice_id: str) -> Voice:
    try:
        return get_voice_store().get(voice_id)
    except VoiceNotFoundError:
        raise HTTPException(status_code=404, detail=f"voice {voice_id!r} not found")  # noqa: B904


@router.delete("/v1/audio/voices/{voice_id}")
async def delete_voice(voice_id: str) -> dict:
    try:
        get_voice_store().delete(voice_id)
    except VoiceNotFoundError:
        raise HTTPException(status_code=404, detail=f"voice {voice_id!r} not found")  # noqa: B904
    return {"id": voice_id, "object": "voice", "deleted": True}


register_capability_endpoints(router, name="speech", base_path="/v1/audio/speech")
