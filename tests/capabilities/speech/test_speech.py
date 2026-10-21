from pathlib import Path

import numpy as np
import pytest
import soundfile as sf  # type: ignore[import-untyped]
from pydantic import ValidationError as PydanticValidationError

from kiapi.capabilities import ValidationError
from kiapi.capabilities.speech import (
    SpeechRequest,
    VoiceNotFoundError,
    VoiceStore,
    resolve_language,
    validate_speech,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "auto"),
        ("", "auto"),
        ("auto", "auto"),
        ("ja", "japanese"),
        ("ja-JP", "japanese"),
        ("en_US", "english"),
        ("Japanese", "japanese"),
        ("zh-Hans-CN", "chinese"),
    ],
)
def test_resolve_language(value: str | None, expected: str) -> None:
    assert resolve_language(value) == expected


def test_resolve_language_rejects_unsupported() -> None:
    with pytest.raises(ValidationError, match="not supported"):
        resolve_language("fi-FI")


def test_validate_speech_accepts_defaults() -> None:
    validate_speech(SpeechRequest(input="こんにちは", voice="voice_0123456789abcdef"))


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        ({"speed": 1.5}, "speed"),
        ({"instructions": "cheerful"}, "instructions"),
        ({"language": "xx"}, "not supported"),
        ({"input": "あ" * 4097}, "maximum"),
    ],
)
def test_validate_speech_rejects(extra: dict, message: str) -> None:
    req = SpeechRequest.model_validate(
        {"input": "こんにちは", "voice": "voice_0123456789abcdef"} | extra
    )
    with pytest.raises(ValidationError, match=message):
        validate_speech(req)


def test_speech_request_rejects_unknown_format() -> None:
    with pytest.raises(PydanticValidationError):
        SpeechRequest.model_validate(
            {"input": "a", "voice": "v", "response_format": "mp3"}
        )


def _tone(path: Path, seconds: float, rate: int = 16_000) -> Path:
    t = np.arange(int(seconds * rate)) / rate
    sf.write(path, 0.2 * np.sin(2 * np.pi * 220 * t), rate)
    return path


def test_voice_store_round_trip(tmp_path: Path) -> None:
    store = VoiceStore(tmp_path / "voices")
    voice = store.create(
        _tone(tmp_path / "ref.wav", 2.0),
        name="tone",
        transcript=" あいうえお ",
        min_seconds=1.0,
        max_seconds=30.0,
    )

    assert voice.id.startswith("voice_")
    assert voice.transcript == "あいうえお"
    assert voice.duration_s == pytest.approx(2.0, abs=0.01)
    assert store.get(voice.id) == voice
    assert [v.id for v in store.list()] == [voice.id]
    data, rate = sf.read(store.reference_path(voice.id))
    assert rate == 24_000
    assert len(data) == pytest.approx(48_000, abs=10)

    store.delete(voice.id)
    assert store.list() == []
    with pytest.raises(VoiceNotFoundError):
        store.get(voice.id)


def test_voice_store_cuts_long_reference(tmp_path: Path) -> None:
    store = VoiceStore(tmp_path)
    voice = store.create(
        _tone(tmp_path / "ref.wav", 5.0),
        name=None,
        transcript=None,
        min_seconds=1.0,
        max_seconds=3.0,
    )

    assert voice.duration_s == pytest.approx(3.0, abs=0.01)
    assert voice.transcript is None


def test_voice_store_sets_transcript(tmp_path: Path) -> None:
    store = VoiceStore(tmp_path)
    voice = store.create(
        _tone(tmp_path / "ref.wav", 2.0),
        name=None,
        transcript=None,
        min_seconds=1.0,
        max_seconds=30.0,
    )

    updated = store.set_transcript(voice.id, " こんにちは ")
    assert updated.transcript == "こんにちは"
    assert store.get(voice.id) == updated
    assert store.set_transcript(voice.id, " ").transcript is None


def test_voice_store_rejects_short_reference(tmp_path: Path) -> None:
    store = VoiceStore(tmp_path)
    with pytest.raises(ValidationError, match="at least"):
        store.create(
            _tone(tmp_path / "ref.wav", 0.5),
            name=None,
            transcript=None,
            min_seconds=1.0,
            max_seconds=30.0,
        )


@pytest.mark.parametrize("voice_id", ["../etc", "voice_../../x", "alloy"])
def test_voice_store_rejects_foreign_ids(tmp_path: Path, voice_id: str) -> None:
    with pytest.raises(VoiceNotFoundError):
        VoiceStore(tmp_path).get(voice_id)
