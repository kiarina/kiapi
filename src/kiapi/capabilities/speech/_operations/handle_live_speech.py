import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from kiapi.capabilities.speech.live import TextSource
from kiapi.core.app import AppContext
from kiapi.core.job import Job, JobCanceledError
from kiapi.core.model import model_registry

from .._helpers.patch_mlx_audio import clear_pending_prime
from .._views.speech_request import SpeechRequest
from .handle_speech import resolve_speech_params


def handle_live_speech(
    ctx: AppContext,
    req: SpeechRequest,
    source: TextSource,
    job: Job,
    emit: Callable[[bytes | dict[str, Any]], None],
) -> tuple[dict[str, Any], list[str]]:
    import mlx.core as mx
    import numpy as np
    from mlx_audio.utils import load_audio  # type: ignore[import-untyped]

    from kiapi.capabilities.speech.live import generate_live, prepare_clone

    if job.cancel_requested():
        raise JobCanceledError()
    spec = model_registry.resolve("speech", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_speech_params(req, variant=spec.name, stream=True)
    if not params.reference_text:
        raise ValueError("Streaming clone requires a reference transcript")
    payload: Any = ctx.memory_manager.acquire(spec)
    source.bind(payload.model.tokenizer)
    cache = getattr(payload, "live_prompts", None)
    if cache is None:
        cache = payload.live_prompts = OrderedDict()
    digest = hashlib.sha256(params.reference_path.read_bytes()).hexdigest()
    key = (params.voice, digest, params.reference_text, params.lang_code)
    clear_pending_prime()
    if key not in cache:
        audio = load_audio(str(params.reference_path), sample_rate=24000)
        cache[key] = prepare_clone(
            payload.model, audio, params.reference_text, params.lang_code
        )
        while len(cache) > 4:
            cache.popitem(last=False)
    cache.move_to_end(key)
    prompt = cache[key]
    emit({"type": "ready", "required_prefix_tokens": prompt.required_prefix_tokens})
    mx.random.seed(params.seed)
    samples = 0
    started = time.monotonic()
    chunks = generate_live(payload.model, prompt, source, emit_frames=4)
    try:
        for audio in chunks:
            if job.cancel_requested():
                raise JobCanceledError()
            pcm = (np.clip(np.array(audio), -1, 1) * 32767).astype("<i2").tobytes()
            emit(pcm)
            samples += len(pcm) // 2
    except InterruptedError:
        raise JobCanceledError() from None
    finally:
        chunks.close()
        clear_pending_prime()
    return {
        "sample_rate": 24000,
        "duration_s": samples / 24000,
        "total_s": time.monotonic() - started,
    }, []
