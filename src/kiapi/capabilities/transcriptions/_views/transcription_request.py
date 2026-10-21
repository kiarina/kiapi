"""OpenAI-compatible ``/v1/audio/transcriptions`` form fields (all but ``file``)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TranscriptionRequest(BaseModel):
    """Form fields of a transcription (OpenAI `audio/transcriptions` compatible)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    model: str | None = Field(
        default=None,
        title="Model",
        description=(
            "Transcription model. Omit for the family default (`qwen3-asr-1.7b`). "
            "OpenAI names such as `whisper-1` are not accepted. Discover models "
            "at GET /v1/audio/transcriptions/models."
        ),
    )
    language: str | None = Field(
        default=None,
        title="Language",
        description=(
            "Language of the audio as an ISO 639 code or name (`ja`, `ja-JP`, "
            "`japanese`). Omit to detect it."
        ),
        examples=["ja"],
    )
    prompt: str | None = Field(
        default=None,
        max_length=2000,
        title="Prompt",
        description=(
            "Context for the speech: the topic, names, or terms it may contain. "
            "Passed to Qwen3-ASR as its context."
        ),
    )
    response_format: Literal["json", "text", "verbose_json"] = Field(
        default="json",
        title="Response format",
        description=(
            "`json` returns `{text}`, `text` returns plain text, and "
            "`verbose_json` adds the language, duration, and timestamps. "
            "`srt`, `vtt`, and `diarized_json` are not supported."
        ),
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        title="Temperature",
        description="Sampling temperature. 0 (default) decodes greedily.",
    )
    timestamp_granularities: list[Literal["segment", "word"]] = Field(
        default=["segment"],
        alias="timestamp_granularities[]",
        title="Timestamp granularities",
        description=(
            "With `verbose_json`, `segment` (default) adds `segments` and `word` "
            "adds `words`. Word timestamps need one of Chinese, Cantonese, "
            "English, German, Spanish, French, Italian, Portuguese, Russian, "
            "Korean, or Japanese."
        ),
    )
