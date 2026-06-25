from typing import Any

from .._services.gcp_relay import GCPRelay
from .._settings import GCPRelaySettings, settings_manager


def create_gcp_relay(**overrides: Any) -> GCPRelay:
    settings = settings_manager.get_settings()
    if overrides:
        settings = GCPRelaySettings.model_validate(
            settings.model_dump() | overrides,
        )
    return GCPRelay(settings)
