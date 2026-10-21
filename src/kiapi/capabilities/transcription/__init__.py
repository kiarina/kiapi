"""transcription family — OpenAI-compatible speech-to-text (Qwen3-ASR on mlx-audio).

Endpoint: ``POST /v1/audio/transcriptions`` (multipart/form-data, like OpenAI).
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiapi.capabilities import ValidationError

    from ._helpers.register import register
    from ._helpers.resolve_language import resolve_language
    from ._helpers.segment_sentences import join_texts, segment_sentences
    from ._helpers.validate_transcription import validate_transcription
    from ._operations.handle_transcription import (
        handle_transcription,
        resolve_transcription_params,
    )
    from ._settings import settings_manager
    from ._views.transcription_request import TranscriptionRequest

__all__ = [
    "TranscriptionRequest",
    "ValidationError",
    "handle_transcription",
    "join_texts",
    "register",
    "resolve_language",
    "resolve_transcription_params",
    "segment_sentences",
    "settings_manager",
    "validate_transcription",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        # kiapi.capabilities
        "ValidationError": "kiapi.capabilities",
        # _helpers
        "join_texts": "._helpers.segment_sentences",
        "register": "._helpers.register",
        "resolve_language": "._helpers.resolve_language",
        "segment_sentences": "._helpers.segment_sentences",
        "validate_transcription": "._helpers.validate_transcription",
        # _operations
        "handle_transcription": "._operations.handle_transcription",
        "resolve_transcription_params": "._operations.handle_transcription",
        # _settings
        "settings_manager": "._settings",
        # _views
        "TranscriptionRequest": "._views.transcription_request",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
