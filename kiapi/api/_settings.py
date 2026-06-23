from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class APISettings(BaseSettings):
    """Settings for API server binding, authentication, and sync request waits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_",
        extra="ignore",
    )

    host: str = Field(
        default="127.0.0.1",
        title="Bind host",
        description=(
            "Hostname or IP address that the kiapi API server binds to.\n"
            "Use 127.0.0.1 for local-only access, or 0.0.0.0 in a trusted "
            "environment when other devices on the same network should connect."
        ),
    )

    port: int = Field(
        default=8000,
        title="Bind port",
        description="TCP port that the kiapi API server binds to.\nThe usual value is 8000.",
    )

    auth_token: SecretStr | None = Field(
        default=None,
        title="API auth token",
        description=(
            "When set, API calls must use Bearer token authentication.\n"
            "When unset, requests are accepted without authentication."
        ),
    )

    sync_timeout_s: float = Field(
        default=600.0,
        title="Sync request wait seconds",
        description=(
            "Maximum number of seconds a sync-mode API call waits for job completion.\n"
            "If this is exceeded, kiapi returns a timeout error instead of "
            "switching the request to async mode."
        ),
    )


settings_manager = SettingsManager(APISettings)
