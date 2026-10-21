"""Transcription API: ``POST /v1/audio/transcriptions`` (OpenAI compatible)."""

import math
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, Response

from kiapi.api import REQUIRE_AUTH, get_ctx, get_worker, register_capability_endpoints
from kiapi.capabilities.transcriptions import (
    ValidationError,
    settings_manager,
    validate_transcription,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.workdir import create_work_dir
from kiapi.core.worker import Worker

from ._operations.run_transcription import run_transcription
from ._views.transcription_form import TranscriptionForm
from ._views.transcription_response import (
    Transcription,
    TranscriptionSegment,
    TranscriptionUsage,
    TranscriptionVerbose,
    TranscriptionWord,
)

router = APIRouter(dependencies=REQUIRE_AUTH)

_CHUNK = 1 << 20


@router.post(
    "/v1/audio/transcriptions",
    response_model=Transcription | TranscriptionVerbose,
    responses={200: {"content": {"text/plain": {"schema": {"type": "string"}}}}},
)
async def create_transcription(
    form: Annotated[TranscriptionForm, Form()],
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response | Transcription | TranscriptionVerbose:
    """Transcribe audio (OpenAI `audio/transcriptions` compatible).

    Send `multipart/form-data` with the audio in `file`. The request waits in
    kiapi's single worker queue while another job runs, and returns when the
    whole file is transcribed (there is no streaming).
    """
    req = form.to_request()
    try:
        model_registry.resolve("transcriptions", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_transcription(req)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    work_dir = create_work_dir("transcriptions")
    try:
        audio_path = await _save_upload(form.file, work_dir)
    except BaseException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    result = await run_transcription(ctx, worker, req, audio_path, work_dir=work_dir)

    usage = TranscriptionUsage(seconds=math.ceil(result["duration_s"]))
    if req.response_format == "text":
        return PlainTextResponse(result["text"])
    if req.response_format == "json":
        return Transcription(text=result["text"], usage=usage)
    words = result["words"]
    return TranscriptionVerbose(
        language=result["language"],
        duration=result["duration_s"],
        text=result["text"],
        segments=(
            [
                TranscriptionSegment(id=i, **segment)
                for i, segment in enumerate(result["segments"])
            ]
            if "segment" in req.timestamp_granularities
            else None
        ),
        words=[TranscriptionWord(**w) for w in words] if words is not None else None,
        usage=usage,
    )


async def _save_upload(file: UploadFile, work_dir: Path) -> Path:
    limit = settings_manager.get_settings().max_file_mb * 1_000_000
    path = work_dir / ("audio" + Path(file.filename or "").suffix.lower())
    size = 0
    with path.open("wb") as out:
        while chunk := await file.read(_CHUNK):
            size += len(chunk)
            if size > limit:
                raise HTTPException(
                    status_code=413,
                    detail=f"file is larger than {limit / 1_000_000:g} MB",
                )
            out.write(chunk)
    if size == 0:
        raise HTTPException(status_code=422, detail="file is empty")
    return path


register_capability_endpoints(
    router, name="transcriptions", base_path="/v1/audio/transcriptions"
)
