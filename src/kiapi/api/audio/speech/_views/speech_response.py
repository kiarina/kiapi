"""``/v1/audio/speech`` result payload for `wav` (the Job ``result``).

Mirrors the dict returned by ``capabilities/speech/_operations/handle_speech``.
"""

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    first_chunk_s: float | None = Field(
        description="Seconds until the first audio chunk."
    )
    total_s: float = Field(description="Wall-clock generation time in seconds.")


class SpeechResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded speech job (`wav`)."""

    file_id: str = Field(description="Files-API id of the produced WAV.")
    audio_bytes: int = Field(description="Size of the produced WAV in bytes.")
    model: str = Field(description="Resolved model.")
    voice: str = Field(description="Voice id that was cloned.")
    language: str = Field(description="Qwen3-TTS language name, or `auto`.")
    sample_rate: int = Field(description="Always 24000.")
    duration_s: float = Field(description="Length of the speech in seconds.")
    canceled: bool = Field(description="Whether generation stopped early.")
    timings: _Timings
