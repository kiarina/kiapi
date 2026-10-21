"""Transcription capability settings, read from the environment (``KIAPI_TRANSCRIPTIONS_``)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class TranscriptionSettings(BaseSettings):
    """Settings for speech-to-text limits and chunking."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_TRANSCRIPTIONS_",
        extra="ignore",
        protected_namespaces=(),
    )

    max_file_mb: float = Field(
        default=100.0,
        title="Maximum file MB",
        description="Largest upload accepted by `/v1/audio/transcriptions`, in MB.",
    )

    max_audio_seconds: float = Field(
        default=3600.0,
        title="Maximum audio seconds",
        description=(
            "Longest audio accepted. Requests share kiapi's single worker, so a "
            "long file makes every other request wait."
        ),
    )

    chunk_seconds: float = Field(
        default=180.0,
        title="Chunk seconds",
        description=(
            "Audio longer than this is cut at a quiet point and transcribed in "
            "parts. Qwen3-ASR takes up to 20 minutes at once, but memory and time "
            "grow with the length (on Apple M1 Max, 3 minutes need 2.3 GB over "
            "the weights, 20 minutes 11.4 GB). `verbose_json` uses at most 5 minutes, "
            "the forced aligner's limit."
        ),
    )

    tokens_per_second: float = Field(
        default=20.0,
        title="Tokens per second",
        description=(
            "Generated tokens allowed per second of audio, so a decoding loop "
            "cannot run without end."
        ),
    )


settings_manager = SettingsManager(TranscriptionSettings)
