"""OpenAI-compatible ``/v1/audio/speech`` request model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SpeechRequest(BaseModel):
    """Text to speak in a registered voice (OpenAI `audio/speech` compatible)."""

    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        title="Model",
        description=(
            "Speech model. Omit/null for the family default (`qwen3-tts-1.7b`). "
            "Discover models at GET /v1/audio/speech/models."
        ),
    )
    input: str = Field(
        ...,
        min_length=1,
        title="Input",
        description=(
            "Text to speak. Capped by `KIAPI_SPEECH_MAX_INPUT_CHARS` (default 4096). "
            "It is read as written, so leave out markup, lists, and URLs."
        ),
        examples=["こんにちは。今日はいい天気ですね。"],
    )
    voice: str = Field(
        ...,
        min_length=1,
        title="Voice",
        description=(
            "Id of a registered voice (POST /v1/audio/voices). There are no "
            "built-in voices: the speech clones the registered reference."
        ),
        examples=["voice_0123456789abcdef"],
    )
    response_format: Literal["pcm", "wav"] = Field(
        default="pcm",
        title="Response format",
        description=(
            "`pcm` streams raw 24 kHz, 16-bit, mono, little-endian PCM while it is "
            "generated (the first chunk arrives before the rest is generated). "
            "`wav` returns one WAV file when generation finishes."
        ),
    )
    stream_format: Literal["audio"] = Field(
        default="audio",
        title="Stream format",
        description="Only `audio` (raw bytes) is supported; `sse` is not.",
    )
    speed: float = Field(
        default=1.0,
        title="Speed",
        description="Only 1.0 is supported (Qwen3-TTS has no speed control).",
    )
    instructions: str | None = Field(
        default=None,
        title="Instructions",
        description="Not supported by voice cloning; must be empty.",
    )
    language: str | None = Field(
        default=None,
        title="Language",
        description=(
            "kiapi extension. Language of `input` as a BCP 47 tag or name "
            "(`ja`, `ja-JP`, `japanese`). Omit to let the model detect it. "
            "Qwen3-TTS speaks Chinese, English, Japanese, Korean, German, French, "
            "Russian, Portuguese, Spanish, and Italian."
        ),
        examples=["ja"],
    )
    seed: int | None = Field(
        default=None,
        title="Seed",
        description="kiapi extension. Random seed; null picks one.",
    )
