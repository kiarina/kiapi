"""speech family — OpenAI-compatible text-to-speech with voice cloning (Qwen3-TTS on mlx-audio).

Endpoints: ``POST /v1/audio/speech`` (raw PCM streamed while generated, or one
WAV) and ``/v1/audio/voices`` (register, list, get, delete reference voices).
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiapi.capabilities import ValidationError

    from ._helpers.default_voice_name import default_voice_name
    from ._helpers.register import register
    from ._helpers.resolve_language import resolve_language
    from ._helpers.validate_speech import validate_speech
    from ._operations.get_voice_store import get_voice_store
    from ._operations.handle_live_speech import handle_live_speech
    from ._operations.handle_speech import handle_speech
    from ._services.voice_store import VoiceNotFoundError, VoiceStore
    from ._settings import settings_manager
    from ._views.speech_request import SpeechRequest
    from ._views.voice import Voice, VoiceCreateRequest, VoiceList, VoiceUpdateRequest

__all__ = [
    "SpeechRequest",
    "ValidationError",
    "Voice",
    "VoiceCreateRequest",
    "VoiceList",
    "VoiceNotFoundError",
    "VoiceStore",
    "VoiceUpdateRequest",
    "default_voice_name",
    "get_voice_store",
    "handle_live_speech",
    "handle_speech",
    "register",
    "resolve_language",
    "settings_manager",
    "validate_speech",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        # kiapi.capabilities
        "ValidationError": "kiapi.capabilities",
        # _helpers
        "default_voice_name": "._helpers.default_voice_name",
        "register": "._helpers.register",
        "resolve_language": "._helpers.resolve_language",
        "validate_speech": "._helpers.validate_speech",
        # _operations
        "get_voice_store": "._operations.get_voice_store",
        "handle_live_speech": "._operations.handle_live_speech",
        "handle_speech": "._operations.handle_speech",
        # _services
        "VoiceNotFoundError": "._services.voice_store",
        "VoiceStore": "._services.voice_store",
        # _settings
        "settings_manager": "._settings",
        # _views
        "SpeechRequest": "._views.speech_request",
        "Voice": "._views.voice",
        "VoiceCreateRequest": "._views.voice",
        "VoiceList": "._views.voice",
        "VoiceUpdateRequest": "._views.voice",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
