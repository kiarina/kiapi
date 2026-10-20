"""Speech service entry: resolve the voice → acquire (memory budget) → generate.

Body of the speech job's worker-thread thunk. With ``emit`` the PCM chunks go to
the caller as they are generated (`pcm`); without it the audio is collected into
one WAV artifact in the global file store (`wav`).
"""

import io
import random
import time
from collections.abc import Callable

from kiapi.capabilities import ValidationError
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import Job, JobResult
from kiapi.core.model import model_registry

from .._helpers.resolve_language import resolve_language
from .._services.voice_store import VoiceNotFoundError
from .._settings import settings_manager
from .._views.speech_params import SpeechParams
from .._views.speech_request import SpeechRequest
from .get_voice_store import get_voice_store


def resolve_speech_params(
    req: SpeechRequest, *, variant: str, stream: bool
) -> SpeechParams:
    settings = settings_manager.get_settings()
    store = get_voice_store()
    try:
        voice = store.get(req.voice)
    except VoiceNotFoundError:
        raise ValidationError(f"voice {req.voice!r} is not registered") from None
    return SpeechParams(
        model=variant,
        input=req.input,
        voice=voice.id,
        reference_path=store.reference_path(voice.id),
        reference_text=voice.transcript,
        lang_code=resolve_language(req.language),
        stream=stream,
        streaming_interval=settings.streaming_interval,
        prime_tokens=settings.prime_tokens,
        seed=req.seed if req.seed is not None else random.randint(0, 2**31 - 1),
    )


def handle_speech(
    ctx: AppContext,
    req: SpeechRequest,
    *,
    job: Job | None = None,
    emit: Callable[[bytes], None] | None = None,
) -> tuple[JobResult, list[FileID]]:
    spec = model_registry.resolve("speech", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_speech_params(req, variant=spec.name, stream=emit is not None)
    payload = ctx.memory_manager.acquire(spec)
    cancel_requested = job.cancel_requested if job is not None else (lambda: False)

    if emit is not None:
        result = spec.module.run(
            payload, params, emit=emit, cancel_requested=cancel_requested
        )
        return result, []

    parts: list[bytes] = []
    result = spec.module.run(
        payload, params, emit=parts.append, cancel_requested=cancel_requested
    )
    rec = ctx.file_store.put_bytes(
        _wav(b"".join(parts), result["sample_rate"]),
        filename=f"speech_{int(time.time())}.wav",
        content_type="audio/wav",
        meta=result,
    )
    return {"file_id": rec.file_id, "audio_bytes": rec.size, **result}, [rec.file_id]


def _wav(pcm: bytes, sample_rate: int) -> bytes:
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buffer.getvalue()
