import uuid

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class GCPRelaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KIAPI_RELAY_GCP_",
        extra="ignore",
    )

    node_id: str = Field(
        title="Relay node ID",
        description="Unique RTDB node ID for this kiapi instance.",
    )
    source_node_id: str = Field(
        default_factory=lambda: f"node-{uuid.uuid4().hex[:8]}",
        title="Relay source node ID",
        description="Identifies this client when issuing relay requests.",
    )
    database_url: str = Field(
        title="Firebase Realtime Database URL",
        description="Database root URL, for example https://project.firebaseio.com.",
    )
    bucket: str = Field(
        title="GCS bucket",
        description="Bucket used for relay request and response payloads.",
    )
    prefix: str = Field(
        default="kiapi",
        title="Object and RTDB prefix",
        description="Shared prefix used below both RTDB and GCS roots.",
    )
    google_settings_key: str | None = Field(
        default=None,
        title="Google settings key",
        description=(
            "Named kiarina.lib.google settings entry used for RTDB and GCS access."
        ),
    )
    lifecycle_age_days: int = Field(
        default=1,
        ge=1,
        title="GCS lifecycle age days",
        description=(
            "Delete relay session objects after this many days. "
            "The matching bucket lifecycle rule is installed at startup."
        ),
    )
    manage_bucket_lifecycle: bool = Field(
        default=True,
        title="Manage GCS lifecycle",
        description="Install the prefix-scoped delete lifecycle rule at startup.",
    )
    reconnect_delay_s: float = Field(
        default=1.0,
        gt=0,
        title="RTDB reconnect delay seconds",
        description="Delay before reconnecting the RTDB SSE watch after an error.",
    )
    request_poll_interval_s: float = Field(
        default=0.5,
        gt=0,
        title="RTDB request poll interval seconds",
        description="Delay between response polls when issuing relay requests.",
    )

    @field_validator("node_id", "source_node_id")
    @classmethod
    def validate_node_id(cls, value: str) -> str:
        if not value or "/" in value or value in {".", ".."}:
            raise ValueError("node id must be a non-empty RTDB path segment")
        return value

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith("https://"):
            raise ValueError("database_url must use https")
        return value

    @field_validator("prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        value = value.strip("/")
        if not value:
            raise ValueError("prefix must not be empty")
        return value


settings_manager = SettingsManager(GCPRelaySettings)
