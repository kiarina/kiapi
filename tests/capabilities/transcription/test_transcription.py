from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from kiapi.capabilities import ValidationError
from kiapi.capabilities.transcription import (
    TranscriptionRequest,
    join_texts,
    resolve_language,
    resolve_transcription_params,
    segment_sentences,
    validate_transcription,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("auto", None),
        ("ja", "Japanese"),
        ("ja-JP", "Japanese"),
        ("en_US", "English"),
        ("japanese", "Japanese"),
        ("yue", "Cantonese"),
        ("fi", "Finnish"),
    ],
)
def test_resolve_language(value: str | None, expected: str | None) -> None:
    assert resolve_language(value) == expected


def test_resolve_language_rejects_unsupported() -> None:
    with pytest.raises(ValidationError, match="not supported"):
        resolve_language("xx")


def test_request_reads_openai_form_names() -> None:
    req = TranscriptionRequest.model_validate(
        {"response_format": "verbose_json", "timestamp_granularities[]": ["word"]}
    )
    assert req.timestamp_granularities == ["word"]
    assert TranscriptionRequest().timestamp_granularities == ["segment"]


def test_request_rejects_unsupported_format() -> None:
    with pytest.raises(PydanticValidationError):
        TranscriptionRequest(response_format="srt")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"timestamp_granularities[]": ["word"]}, "verbose_json"),
        (
            {
                "response_format": "verbose_json",
                "timestamp_granularities[]": ["word"],
                "language": "fi",
            },
            "not available",
        ),
        ({"language": "xx"}, "not supported"),
    ],
)
def test_validate_transcription_rejects(fields: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        validate_transcription(TranscriptionRequest.model_validate(fields))


def test_params_align_only_for_verbose_json() -> None:
    plain = resolve_transcription_params(
        TranscriptionRequest(), Path("a.wav"), variant="qwen3-asr-1.7b"
    )
    assert not plain.align and not plain.words
    verbose = resolve_transcription_params(
        TranscriptionRequest.model_validate(
            {"response_format": "verbose_json", "timestamp_granularities[]": ["word"]}
        ),
        Path("a.wav"),
        variant="qwen3-asr-1.7b",
    )
    assert verbose.align and verbose.words


def _w(word: str, start: float, end: float) -> dict:
    return {"word": word, "start": start, "end": end}


def test_segment_sentences_japanese() -> None:
    words = [
        _w("もしもし", 0.1, 0.7),
        _w("着い", 0.8, 1.2),
        _w("た", 1.2, 1.4),
        _w("うん", 2.0, 2.2),
    ]
    assert segment_sentences("もしもし、着いた？うん。", words) == [  # noqa: RUF001
        {"start": 0.1, "end": 1.4, "text": "もしもし、着いた？"},  # noqa: RUF001
        {"start": 2.0, "end": 2.2, "text": "うん。"},
    ]


def test_segment_sentences_english_keeps_decimals() -> None:
    words = [_w("It", 0.0, 0.2), _w("costs", 0.2, 0.5), _w("35", 0.5, 0.9)]
    words += [_w("OK", 1.0, 1.3)]
    assert segment_sentences("It costs 3.5. OK!", words) == [
        {"start": 0.0, "end": 0.9, "text": "It costs 3.5."},
        {"start": 1.0, "end": 1.3, "text": "OK!"},
    ]


def test_segment_sentences_keeps_trailing_words() -> None:
    words = [_w("a", 0.0, 0.1), _w("b", 0.2, 0.3)]
    assert segment_sentences("a", words) == [{"start": 0.0, "end": 0.3, "text": "a"}]


def test_join_texts() -> None:
    assert join_texts(["こんにちは。", "さようなら。"], ["Japanese"] * 2) == (
        "こんにちは。さようなら。"
    )
    assert join_texts(["Hello.", "", "Bye."], ["English", None, "English"]) == (
        "Hello. Bye."
    )
