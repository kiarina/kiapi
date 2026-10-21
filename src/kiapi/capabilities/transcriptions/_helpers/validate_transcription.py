from kiapi.capabilities import ValidationError

from .._views.transcription_request import TranscriptionRequest
from .resolve_language import ALIGN_LANGUAGES, resolve_language


def validate_transcription(req: TranscriptionRequest) -> None:
    language = resolve_language(req.language)
    words = "word" in req.timestamp_granularities
    if words and req.response_format != "verbose_json":
        raise ValidationError(
            "timestamp_granularities needs response_format verbose_json"
        )
    if words and language is not None and language not in ALIGN_LANGUAGES:
        raise ValidationError(f"word timestamps are not available for {language}")
