import uuid
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class LocalRelaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KIAPI_RELAY_LOCAL_",
        extra="ignore",
    )

    node_id: str = Field(
        default="local",
        title="Relay node ID",
        description="Unique local relay node ID for this kiapi instance.",
    )
    source_node_id: str = Field(
        default_factory=lambda: f"node-{uuid.uuid4().hex[:8]}",
        title="Relay source node ID",
        description="Identifies this client when issuing relay requests.",
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

    @field_validator("node_id", "source_node_id")
    @classmethod
    def validate_node_id(cls, value: str) -> str:
        if not value or "/" in value or value in {".", ".."}:
            raise ValueError("node id must be a non-empty path segment")
        return value

    @field_validator("prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        value = value.strip("/")
        if not value:
            raise ValueError("prefix must not be empty")
        return value


settings_manager = SettingsManager(LocalRelaySettings)
