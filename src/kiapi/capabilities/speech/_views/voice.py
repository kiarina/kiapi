"""A registered voice and the request that registers one."""

from typing import Literal

from pydantic import BaseModel, Field

from kiapi.core.file import FileRef


class VoiceCreateRequest(BaseModel):
    """Reference audio (and its transcript) to clone a voice from."""

    audio: FileRef = Field(
        ...,
        title="Audio",
        description=(
            "Reference audio as a file reference: `{type: file_id, file_id}`, "
            "`{type: url, url}`, or `{type: data_url, data_url}`. WAV, "
            "FLAC, MP3, or OGG of one clear speaker; 5 to 15 seconds works well. "
            "It is converted to 24 kHz mono and cut to "
            "`KIAPI_SPEECH_MAX_REFERENCE_SECONDS` (default 30)."
        ),
    )
    name: str | None = Field(
        default=None,
        max_length=200,
        title="Name",
        description="Optional label shown in the voice list.",
    )
    transcript: str | None = Field(
        default=None,
        max_length=2000,
        title="Transcript",
        description=(
            "What the reference says, word for word. Omit it to have kiapi "
            "transcribe the reference (`KIAPI_SPEECH_TRANSCRIBE_REFERENCE`); "
            "without a transcript the voice is cloned from the speaker embedding "
            "only and sounds less like the reference."
        ),
    )


class Voice(BaseModel):
    """A voice registered for `/v1/audio/speech`."""

    id: str = Field(title="Id", description="Pass as `voice` to /v1/audio/speech.")
    object: Literal["voice"] = Field(default="voice", title="Object")
    name: str | None = Field(default=None, title="Name")
    transcript: str | None = Field(
        default=None,
        title="Transcript",
        description=(
            "The reference transcript (given, or transcribed by kiapi), or null "
            "when cloned from the embedding only."
        ),
    )
    duration_s: float = Field(
        title="Duration", description="Reference length in seconds."
    )
    created_at: int = Field(title="Created at", description="Unix seconds.")


class VoiceList(BaseModel):
    object: Literal["list"] = Field(default="list", title="Object")
    data: list[Voice] = Field(title="Data")
