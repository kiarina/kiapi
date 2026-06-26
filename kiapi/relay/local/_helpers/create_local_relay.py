from typing import Any

from .._services.local_relay import LocalRelay
from .._settings import LocalRelaySettings, settings_manager


def create_local_relay(**overrides: Any) -> LocalRelay:
    settings = settings_manager.get_settings()
    if overrides:
        settings = LocalRelaySettings.model_validate(
            settings.model_dump() | overrides,
        )
    return LocalRelay(settings)
