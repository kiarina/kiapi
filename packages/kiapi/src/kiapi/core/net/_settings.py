"""Networking guard defaults, read from the environment (``KIAPI_NET_``)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class NetSettings(BaseSettings):
    """Network safety settings for accessing user-provided URLs."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_NET_",
        extra="ignore",
        protected_namespaces=(),
    )

    allow_private_urls: bool = Field(
        default=False,
        title="Allow private URLs",
        description=(
            "When true, disables the SSRF guard and allows URLs that resolve to "
            "private, loopback, or link-local addresses.\n"
            "Enable this only in a trusted local development environment."
        ),
    )


settings_manager = SettingsManager(NetSettings)
