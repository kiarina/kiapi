"""Resolved speech parameters passed to the model layer."""

from pathlib import Path

from pydantic import BaseModel


class SpeechParams(BaseModel):
    model: str
    input: str
    voice: str
    reference_path: Path
    reference_text: str | None
    lang_code: str
    stream: bool
    streaming_interval: float
    prime_tokens: int
    seed: int
