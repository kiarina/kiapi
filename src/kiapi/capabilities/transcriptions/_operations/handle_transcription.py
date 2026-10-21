"""Transcription service entry: resolve → acquire (memory budget) → transcribe.

Body of the transcription job's worker-thread thunk.
"""

from pathlib import Path

from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._helpers.resolve_language import resolve_language
from .._settings import settings_manager
from .._views.transcription_params import TranscriptionParams
from .._views.transcription_request import TranscriptionRequest

# Qwen3-ForcedAligner times at most 5 minutes of speech.
ALIGN_MAX_SECONDS = 300.0


def resolve_transcription_params(
    req: TranscriptionRequest, audio_path: Path, *, variant: str
) -> TranscriptionParams:
    settings = settings_manager.get_settings()
    align = req.response_format == "verbose_json"
    return TranscriptionParams(
        model=variant,
        audio_path=audio_path,
        language=resolve_language(req.language),
        prompt=(req.prompt or "").strip() or None,
        temperature=req.temperature,
        align=align,
        words=align and "word" in req.timestamp_granularities,
        chunk_seconds=(
            min(settings.chunk_seconds, ALIGN_MAX_SECONDS)
            if align
            else settings.chunk_seconds
        ),
        max_audio_seconds=settings.max_audio_seconds,
        tokens_per_second=settings.tokens_per_second,
    )


def handle_transcription(
    ctx: AppContext, req: TranscriptionRequest, audio_path: Path
) -> tuple[JobResult, list[FileID]]:
    spec = model_registry.resolve("transcriptions", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_transcription_params(req, audio_path, variant=spec.name)
    payload = ctx.memory_manager.acquire(spec)
    return spec.module.run(payload, params), []
