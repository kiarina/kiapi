"""Ideogram 4 capability defaults + caps, read from ``KIAPI_IDEOGRAM4_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class Ideogram4Settings(BaseSettings):
    """Settings for the Ideogram 4 model, image sizes, presets, and quantization."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_IDEOGRAM4_",
        extra="ignore",
        protected_namespaces=(),
    )

    model_repo: str = Field(
        default="ideogram-ai/ideogram-4-fp8",
        title="Ideogram 4 model repo",
        description="Hugging Face repo ID for the Ideogram 4 model used for image generation.",
    )

    # --------------------------------------------------
    # generate
    # --------------------------------------------------

    default_width: int = Field(
        default=1024,
        title="Default width",
        description="Output image width in pixels used when a request omits width.",
    )

    default_height: int = Field(
        default=1024,
        title="Default height",
        description="Output image height in pixels used when a request omits height.",
    )

    min_width: int = Field(
        default=256,
        title="Minimum width",
        description="Lower pixel limit for the output image width accepted in a request.",
    )

    min_height: int = Field(
        default=256,
        title="Minimum height",
        description="Lower pixel limit for the output image height accepted in a request.",
    )

    max_width: int = Field(
        default=2048,
        title="Maximum width",
        description="Upper pixel limit for the output image width accepted in a request.",
    )

    max_height: int = Field(
        default=2048,
        title="Maximum height",
        description="Upper pixel limit for the output image height accepted in a request.",
    )

    default_preset: str = Field(
        default="V4_DEFAULT_20",
        title="Default preset",
        description=(
            "Ideogram 4 preset name used when a request omits preset.\n"
            "The value must be included in presets."
        ),
    )

    presets: tuple[str, ...] = Field(
        default=("V4_DEFAULT_20", "V4_QUALITY_48", "V4_TURBO_12"),
        title="Available presets",
        description="List of Ideogram 4 preset names accepted by the API.",
    )

    default_quantize: int | None = Field(
        default=None,
        title="Default quantization bits",
        description=(
            "Default quantization bit count used when loading the Ideogram 4 model.\n"
            "When None, the model repo's default precision is used. A numeric "
            "value quantizes to that bit count."
        ),
    )


settings_manager = SettingsManager(Ideogram4Settings)
