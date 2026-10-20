from pathlib import Path

from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    import tempfile

    import numpy as np
    import soundfile as sf  # type: ignore

    from kiapi.capabilities.speech import SpeechRequest, get_voice_store, handle_speech

    # A one-second tone is enough to exercise the voice-clone path end to end.
    with tempfile.TemporaryDirectory() as tmp:
        reference = Path(tmp) / "reference.wav"
        t = np.arange(24_000) / 24_000
        sf.write(reference, 0.2 * np.sin(2 * np.pi * 220 * t), 24_000)
        store = get_voice_store()
        voice = store.create(
            reference,
            name="kiapi check",
            transcript="あ",
            min_seconds=1.0,
            max_seconds=30.0,
        )
    try:
        result, artifacts = handle_speech(
            ctx,
            SpeechRequest(
                model=spec.name,
                input="テスト。",
                voice=voice.id,
                response_format="wav",
                language="ja",
                seed=1,
            ),
        )
    finally:
        store.delete(voice.id)
    return build_check_result(spec, result, artifacts)
