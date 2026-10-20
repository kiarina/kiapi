from kiarina.utils.app import user_directory

from .._services.voice_store import VoiceStore
from .._settings import settings_manager


def get_voice_store() -> VoiceStore:
    settings = settings_manager.get_settings()
    root = (
        settings.voices_dir or user_directory.get_user_data_dir() / "speech" / "voices"
    )
    return VoiceStore(root)
