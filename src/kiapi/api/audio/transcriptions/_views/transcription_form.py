"""The multipart form: the audio ``file`` and the transcription fields."""

from fastapi import UploadFile
from pydantic import Field

from kiapi.capabilities.transcriptions import TranscriptionRequest


class TranscriptionForm(TranscriptionRequest):
    """Audio and options to transcribe (OpenAI `audio/transcriptions` compatible)."""

    file: UploadFile = Field(
        title="File",
        description=(
            "Audio to transcribe: WAV, FLAC, MP3, OGG, M4A, or the audio of a "
            "video. Capped by `KIAPI_TRANSCRIPTIONS_MAX_FILE_MB` (default 100) "
            "and `KIAPI_TRANSCRIPTIONS_MAX_AUDIO_SECONDS` (default 3600)."
        ),
    )

    def to_request(self) -> TranscriptionRequest:
        return TranscriptionRequest.model_validate(self.model_dump(exclude={"file"}))
