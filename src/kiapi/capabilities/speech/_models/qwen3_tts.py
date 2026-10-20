"""Handler for Qwen3-TTS 1.7B Base on MLX (mlx-audio): voice cloning, streamed.

Each generated chunk is handed to ``emit`` as 24 kHz, 16-bit, mono,
little-endian PCM bytes. The streaming fixes live in ``patch_mlx_audio``.
"""

import time
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from kiapi.core.model import ModelSpec

from .._helpers.patch_mlx_audio import (
    clear_pending_prime,
    patch_mlx_audio,
    set_prime_tokens,
)
from .._views.speech_params import SpeechParams

FEATURES = {"text", "voice_clone", "streaming"}
SAMPLE_RATE = 24_000


def load(spec: ModelSpec) -> SimpleNamespace:
    from mlx_audio.tts.utils import load_model  # type: ignore

    patch_mlx_audio()
    return SimpleNamespace(model=load_model(spec.repo))


def run(
    payload: SimpleNamespace,
    params: SpeechParams,
    *,
    emit: Callable[[bytes], None],
    cancel_requested: Callable[[], bool],
) -> dict[str, Any]:
    import mlx.core as mx
    import numpy as np

    model = payload.model
    mx.random.seed(params.seed)
    clear_pending_prime()
    set_prime_tokens(params.prime_tokens)

    kwargs: dict[str, Any] = {
        "text": params.input,
        "ref_audio": str(params.reference_path),
        "lang_code": params.lang_code,
    }
    if params.reference_text:
        kwargs["ref_text"] = params.reference_text
    if params.stream:
        kwargs.update(stream=True, streaming_interval=params.streaming_interval)

    samples = 0
    first_chunk_s = None
    canceled = False
    t0 = time.time()
    chunks = model.generate(**kwargs)
    try:
        for result in chunks:
            if cancel_requested():
                canceled = True
                break
            audio = np.clip(np.array(result.audio, dtype=np.float32), -1.0, 1.0)
            pcm = (audio * 32767.0).astype("<i2").tobytes()
            if first_chunk_s is None:
                first_chunk_s = round(time.time() - t0, 3)
            samples += len(audio)
            emit(pcm)
    finally:
        chunks.close()
        clear_pending_prime()

    return {
        "model": params.model,
        "voice": params.voice,
        "language": params.lang_code,
        "sample_rate": SAMPLE_RATE,
        "duration_s": round(samples / SAMPLE_RATE, 3),
        "canceled": canceled,
        "timings": {
            "first_chunk_s": first_chunk_s,
            "total_s": round(time.time() - t0, 3),
        },
    }
