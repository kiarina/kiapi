"""Speech capability settings, read from the environment (``KIAPI_SPEECH_``)."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class SpeechSettings(BaseSettings):
    """Settings for text-to-speech limits, streaming, and the voice store."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_SPEECH_",
        extra="ignore",
        protected_namespaces=(),
    )

    voices_dir: Path | None = Field(
        default=None,
        title="Voices directory",
        description=(
            "Where registered voices (reference audio and transcript) are kept.\n"
            "Unset uses `speech/voices` under the kiapi user data directory."
        ),
    )

    max_input_chars: int = Field(
        default=4096,
        title="Maximum input characters",
        description="Maximum length of `input` accepted by `/v1/audio/speech`.",
    )

    max_reference_seconds: float = Field(
        default=30.0,
        title="Maximum reference seconds",
        description=(
            "Reference audio longer than this is cut to its first seconds when a "
            "voice is registered."
        ),
    )

    min_reference_seconds: float = Field(
        default=1.0,
        title="Minimum reference seconds",
        description="Reference audio shorter than this is rejected.",
    )

    transcribe_reference: bool = Field(
        default=True,
        title="Transcribe references",
        description=(
            "When a voice is registered without a transcript, transcribe the "
            "reference with the transcription family. Skipped (with a warning) "
            "while that model is not activated."
        ),
    )

    streaming_interval: float = Field(
        default=0.5,
        title="Streaming chunk seconds",
        description="Seconds of audio decoded per chunk when streaming PCM.",
    )

    prime_tokens: int = Field(
        default=12,
        title="Streaming decoder priming tokens",
        description=(
            "Reference codes (12 per second) passed through the streaming decoder "
            "before the generated codes, so the first chunk is decoded with the "
            "reference as left context. 0 primes with the whole reference."
        ),
    )


settings_manager = SettingsManager(SpeechSettings)
