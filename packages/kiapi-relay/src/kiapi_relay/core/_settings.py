from kiarina.utils.common import ImportPath
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager

from ._types.relay_name import RelayName
from ._types.relay_specifier import RelaySpecifier


class RelaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KIAPI_RELAY_",
        extra="ignore",
    )

    default: RelaySpecifier | None = Field(
        default=None,
        title="Default relay",
        description=(
            "Relay specifier started with the API server.\n"
            "Leave unset to disable remote relay processing."
        ),
    )
    presets: dict[RelayName, ImportPath] = Field(
        default_factory=lambda: {
            "gcp": "kiapi_relay.impl.gcp:create_gcp_relay",
            "local": "kiapi_relay.impl.local:create_local_relay",
        },
        title="Relay presets",
        description="Built-in relay factories keyed by relay name.",
    )
    customs: dict[RelayName, ImportPath] = Field(
        default_factory=dict,
        title="Custom relays",
        description="Custom relay factories keyed by relay name.",
    )


settings_manager = SettingsManager(RelaySettings)
