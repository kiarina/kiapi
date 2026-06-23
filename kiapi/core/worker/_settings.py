from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager

from kiapi.core.model import ModelKey


class WorkerSettings(BaseSettings):
    """Settings for the single worker queue, TTL sweeping, and startup warmup."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_",
        extra="ignore",
    )

    ttl_sweep_interval_s: float = Field(
        default=60.0,
        title="TTL sweep interval seconds",
        description=(
            "Interval for background checks of resident models that exceeded their idle TTL.\n"
            "Set to 0.0 to completely disable the background sweep."
        ),
    )

    warmup_models: list[ModelKey] = Field(
        default_factory=list,
        title="Startup warmup models",
        description=(
            "List of model keys to preload when the server starts.\n"
            "Each item uses the model registry key format. An empty list keeps "
            "models lazily loaded."
        ),
    )


settings_manager = SettingsManager(WorkerSettings)
