"""Depth Pro capability defaults + caps, read from ``KIAPI_DEPTHPRO_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class DepthProSettings(BaseSettings):
    """Settings for Depth Pro quantization, input image limits, and progress display."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_DEPTHPRO_",
        extra="ignore",
        protected_namespaces=(),
    )

    default_quantize: int | None = Field(
        default=8,
        title="Default quantization bits",
        description=(
            "Default quantization bit count used when loading the Depth Pro model.\n"
            "Use a bit count such as 8, or None to disable quantization."
        ),
    )

    max_input_pixels: int = Field(
        default=4096 * 4096,
        title="Maximum input pixels",
        description=(
            "Maximum total pixel count for an input image passed to Depth Pro.\n"
            "This protects the single worker queue from being blocked for a long "
            "time by very large images."
        ),
    )

    progress_eta_s: float = Field(
        default=8.0,
        title="Progress ETA seconds",
        description=(
            "Expected processing seconds used to show synthetic progress while Depth Pro runs.\n"
            "Set to 0 to keep progress at the coarse value until completion."
        ),
    )


settings_manager = SettingsManager(DepthProSettings)
