from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class MemorySettings(BaseSettings):
    """Settings for the model residency memory budget and idle TTL shared by all capabilities."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_",
        extra="ignore",
    )

    memory_limit_gb: float | None = Field(
        default=None,
        title="Memory budget GB",
        description=(
            "Memory budget in GB shared by resident models and runtime peaks across all capabilities.\n"
            "If unset, kiapi uses 80% of the machine's total memory.\n"
            "Before a job starts, lower-priority and older resident models are "
            "released until the job fits within this value."
        ),
    )

    default_ttl_s: float = Field(
        default=1800.0,
        title="Default idle TTL seconds",
        description=(
            "Default number of seconds before an unused resident model is auto-released.\n"
            "Set to 0.0 or less to disable TTL release and evict only under "
            "memory pressure."
        ),
    )


settings_manager = SettingsManager(MemorySettings)
