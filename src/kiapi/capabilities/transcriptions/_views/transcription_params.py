"""Resolved transcription parameters passed to the model layer."""

from pathlib import Path

from pydantic import BaseModel


class TranscriptionParams(BaseModel):
    model: str
    audio_path: Path
    language: str | None
    prompt: str | None
    temperature: float
    align: bool
    words: bool
    chunk_seconds: float
    max_audio_seconds: float
    tokens_per_second: float
