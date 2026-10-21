"""``/v1/audio/transcriptions`` response bodies, in OpenAI's shapes."""

from typing import Literal

from pydantic import BaseModel, Field


class TranscriptionUsage(BaseModel):
    type: Literal["duration"] = Field(default="duration", title="Type")
    seconds: int = Field(title="Seconds", description="Audio length, rounded up.")


class TranscriptionSegment(BaseModel):
    id: int = Field(title="Id")
    start: float = Field(title="Start", description="Start in seconds.")
    end: float = Field(title="End", description="End in seconds.")
    text: str = Field(title="Text")


class TranscriptionWord(BaseModel):
    word: str = Field(title="Word", description="Without punctuation.")
    start: float = Field(title="Start", description="Start in seconds.")
    end: float = Field(title="End", description="End in seconds.")


class Transcription(BaseModel):
    """`json` response."""

    text: str = Field(title="Text")
    usage: TranscriptionUsage = Field(title="Usage")


class TranscriptionVerbose(BaseModel):
    """`verbose_json` response."""

    task: Literal["transcribe"] = Field(default="transcribe", title="Task")
    language: str | None = Field(
        title="Language",
        description="Detected or given language in lower case, comma-separated when it changes.",
    )
    duration: float = Field(title="Duration", description="Audio length in seconds.")
    text: str = Field(title="Text")
    segments: list[TranscriptionSegment] | None = Field(
        default=None,
        title="Segments",
        description=(
            "Sentences timed by the forced aligner, or one per decoded part when "
            "the language has no aligner. Only with `segment` granularity."
        ),
    )
    words: list[TranscriptionWord] | None = Field(
        default=None,
        title="Words",
        description="Only with `word` granularity.",
    )
    usage: TranscriptionUsage = Field(title="Usage")
