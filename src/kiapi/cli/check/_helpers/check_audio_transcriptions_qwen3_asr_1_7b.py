from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    import tempfile
    from pathlib import Path

    import numpy as np
    import soundfile as sf  # type: ignore

    from kiapi.capabilities.transcriptions import (
        TranscriptionRequest,
        handle_transcription,
    )

    # A one-second tone exercises loading and decoding; it transcribes to "".
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "tone.wav"
        t = np.arange(16_000) / 16_000
        sf.write(audio, 0.2 * np.sin(2 * np.pi * 220 * t), 16_000)
        result, artifacts = handle_transcription(
            ctx,
            TranscriptionRequest(model=spec.name, response_format="verbose_json"),
            audio,
        )
    return build_check_result(spec, result, artifacts)
