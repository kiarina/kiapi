from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class LocalRelaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KIAPI_RELAY_LOCAL_",
        extra="ignore",
    )

    root: Path = Field(
        default=Path("/tmp/kiapi/relay"),
        title="Local relay root",
        description="Directory used for local relay request and response payloads.",
    )
    prefix: str = Field(
        default="kiapi",
        title="Local relay prefix",
        description="Shared prefix used below the local relay root.",
    )
    poll_interval_s: float = Field(
        default=0.2,
        gt=0,
        title="Local relay poll interval seconds",
        description="Delay between local request directory scans.",
    )
    heartbeat_interval_s: float = Field(
        default=300.0,
        gt=0,
        title="Liveness heartbeat interval seconds",
        description="How often the kiapi node refreshes its liveness entry.",
    )
    liveness_ttl_s: float = Field(
        default=1800.0,
        gt=0,
        title="Liveness staleness threshold seconds",
        description=(
            "A node is considered usable only when its last heartbeat is newer "
            "than this. Clients pick the most recently seen node within it."
        ),
    )

    @field_validator("prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        value = value.strip("/")
        if not value:
            raise ValueError("prefix must not be empty")
        return value


settings_manager = SettingsManager(LocalRelaySettings)
