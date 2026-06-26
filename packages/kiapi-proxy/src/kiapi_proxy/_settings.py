from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager

from kiapi_relay import RelaySpecifier


class ProxySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KIAPI_PROXY_",
        extra="ignore",
    )

    host: str = Field(
        default="127.0.0.1",
        title="Bind host",
        description="Host the proxy server binds to.",
    )
    port: int = Field(
        default=8080,
        title="Bind port",
        description="Port the proxy server binds to.",
    )
    relay: RelaySpecifier | None = Field(
        default=None,
        title="Relay specifier",
        description=(
            "Relay used to forward requests, for example 'local' or 'gcp'.\n"
            "Leave unset to use the relay's own configured default "
            "(KIAPI_RELAY_DEFAULT)."
        ),
    )
    request_timeout_s: float = Field(
        default=1800.0,
        gt=0,
        title="Request timeout seconds",
        description="Maximum time to wait for a relayed response.",
    )


settings_manager = SettingsManager(ProxySettings)
