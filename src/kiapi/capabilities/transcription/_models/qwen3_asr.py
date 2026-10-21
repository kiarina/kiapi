"""Handler for Qwen3-ASR 1.7B on MLX (mlx-audio), with Qwen3-ForcedAligner for timestamps.

Long audio is cut at quiet points and each part is transcribed on its own, as
the reference toolkit (qwen-asr) does, and its parts are joined without a
separator for languages written without spaces (mlx-audio always adds one).
"""

import math
import time
from types import SimpleNamespace
from typing import Any

from kiapi.capabilities import CapabilityError, ValidationError
from kiapi.core.job import ProgressReporter
from kiapi.core.model import ModelSpec

from .._helpers.resolve_language import ALIGN_LANGUAGES
from .._helpers.segment_sentences import join_texts, segment_sentences
from .._views.transcription_params import TranscriptionParams

FEATURES = {"audio", "timestamps"}
SAMPLE_RATE = 16_000
ALIGNER_REPO = "mlx-community/Qwen3-ForcedAligner-0.6B-bf16"


def load(spec: ModelSpec) -> SimpleNamespace:
    from mlx_audio.stt import load as load_stt  # type: ignore

    return SimpleNamespace(asr=load_stt(spec.repo), aligner=load_stt(ALIGNER_REPO))


def run(payload: SimpleNamespace, params: TranscriptionParams) -> dict[str, Any]:
    import mlx.core as mx
    import numpy as np
    from mlx_audio.stt.models.qwen3_asr.qwen3_asr import (  # type: ignore
        split_audio_into_chunks,
    )
    from mlx_audio.stt.utils import load_audio  # type: ignore

    t0 = time.time()
    try:
        audio = np.array(
            load_audio(str(params.audio_path), duration=params.max_audio_seconds + 1)
        )
    except Exception as exc:
        raise ValidationError(f"could not read the audio: {exc}") from exc
    duration = len(audio) / SAMPLE_RATE
    if duration > params.max_audio_seconds:
        raise ValidationError(
            f"audio is longer than the maximum of {params.max_audio_seconds:g}s"
        )

    chunks = split_audio_into_chunks(
        audio, sr=SAMPLE_RATE, chunk_duration=params.chunk_seconds
    )
    ends = [offset for _, offset in chunks[1:]] + [duration]
    progress = ProgressReporter.current()
    steps = len(chunks) * (2 if params.align else 1)

    texts: list[str] = []
    languages: list[str | None] = []
    for i, (wav, _offset) in enumerate(chunks):
        progress.step(i, steps, "transcribing")
        out = payload.asr.generate(
            wav,
            language=params.language,
            system_prompt=params.prompt,
            temperature=params.temperature,
            max_tokens=max(
                256, math.ceil(len(wav) / SAMPLE_RATE * params.tokens_per_second)
            ),
            chunk_duration=math.inf,
        )
        language = params.language or out.language[0]
        texts.append(out.text.strip())
        languages.append(None if language in (None, "", "None") else language)
        mx.clear_cache()

    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []
    for i, ((wav, offset), end, text, language) in enumerate(
        zip(chunks, ends, texts, languages, strict=True)
    ):
        if not text:
            continue
        if not params.align or language not in ALIGN_LANGUAGES:
            if params.words:
                raise CapabilityError(
                    f"word timestamps are not available for {language or 'this audio'}"
                )
            segments.append(
                {"start": round(offset, 3), "end": round(end, 3), "text": text}
            )
            continue
        progress.step(len(chunks) + i, steps, "aligning")
        aligned = payload.aligner.generate(wav, text=text, language=language)
        chunk_words = [
            {
                "word": item.text,
                "start": round(offset + item.start_time, 3),
                "end": round(offset + item.end_time, 3),
            }
            for item in aligned
        ]
        words.extend(chunk_words)
        segments.extend(segment_sentences(text, chunk_words))
        mx.clear_cache()

    detected = [lang for lang in languages if lang]
    return {
        "model": params.model,
        "text": join_texts(texts, languages),
        "language": ",".join(dict.fromkeys(detected)).lower() or None,
        "duration_s": round(duration, 3),
        "segments": segments,
        "words": words if params.words else None,
        "timings": {"total_s": round(time.time() - t0, 3)},
    }
