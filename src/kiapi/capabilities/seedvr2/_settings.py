"""SeedVR2 capability defaults + caps, read from ``KIAPI_SEEDVR2_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class SeedVR2Settings(BaseSettings):
    """Settings for the SeedVR2 upscaling model, scale factors, and resolution limits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_SEEDVR2_",
        extra="ignore",
        protected_namespaces=(),
    )

    model_repo: str = Field(
        default="numz/SeedVR2_comfyUI",
        title="SeedVR2 model repo",
        description="Hugging Face repo ID for the SeedVR2 model used for video and image upscaling.",
    )

    # --------------------------------------------------
    # upscale
    # --------------------------------------------------

    default_resolution: str = Field(
        default="2x",
        title="Default output resolution",
        description=(
            "Upscaling resolution used when a request omits resolution.\n"
            "Use a scale notation such as 2x, or another resolution value "
            "accepted by the implementation."
        ),
    )

    default_softness: float = Field(
        default=0.0,
        title="Default softness",
        description=(
            "Correction amount used when a request omits softness.\n"
            "0.0 is the baseline; higher values produce softer results."
        ),
    )

    default_quantize: int | None = Field(
        default=8,
        title="Default quantization bits",
        description=(
            "Default quantization bit count used when loading the SeedVR2 model.\n"
            "Use a bit count such as 8, or None to disable quantization."
        ),
    )

    max_scale: float = Field(
        default=4.0,
        title="Maximum scale factor",
        description="Upper limit for the upscaling scale factor accepted in a request.",
    )

    max_resolution: int = Field(
        default=2048,
        title="Maximum output resolution",
        description="Upper pixel limit for the output width or height accepted in a request.",
    )

    min_resolution: int = Field(
        default=16,
        title="Minimum output resolution",
        description="Lower pixel limit for the output width or height accepted in a request.",
    )


settings_manager = SettingsManager(SeedVR2Settings)
