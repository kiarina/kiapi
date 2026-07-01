from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class GCPRelaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KIAPI_RELAY_GCP_",
        extra="ignore",
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
        default="",
        title="Object and RTDB prefix",
        description=(
            "Shared prefix used below both RTDB and GCS roots. "
            "Leave empty to use the bucket and database roots directly."
        ),
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
        # An empty prefix is allowed and places relay objects at the bucket and
        # database roots. Stripping slashes keeps path joins free of leading or
        # doubled separators.
        return value.strip("/")


settings_manager = SettingsManager(GCPRelaySettings)
