"""Qwen Image capability defaults + caps, read from ``KIAPI_QWEN_`` env vars."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class QwenSettings(BaseSettings):
    """Settings for Qwen Image models, generation defaults, and LoRA limits."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_QWEN_",
        extra="ignore",
        protected_namespaces=(),
    )

    image_model: str = Field(
        default="Qwen/Qwen-Image",
        title="Image generation model repo",
        description="Hugging Face repo ID used for Qwen Image text-to-image generation.",
    )

    edit_model: str = Field(
        default="Qwen/Qwen-Image-Edit-2509",
        title="Image editing model repo",
        description="Hugging Face repo ID used for Qwen Image editing.",
    )

    default_quantize: int | None = Field(
        default=8,
        title="Default quantization bits",
        description=(
            "Default quantization bit count used when loading the Qwen Image model.\n"
            "Use a bit count such as 8, or None to disable quantization."
        ),
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

    max_steps: int = Field(
        default=100,
        title="Maximum inference steps",
        description="Upper limit for the diffusion step count accepted in a request.",
    )

    max_loras: int = Field(
        default=4,
        title="Maximum LoRA count",
        description="Maximum number of LoRA adapters that can be applied in one generation or edit request.",
    )

    generate_steps: int = Field(
        default=30,
        title="Default generation steps",
        description="Diffusion step count used when a text-to-image request omits steps.",
    )

    generate_guidance: float = Field(
        default=4.0,
        title="Default generation guidance",
        description="Guidance strength used when a text-to-image request omits guidance.",
    )

    # --------------------------------------------------
    # edit
    # --------------------------------------------------

    edit_steps: int = Field(
        default=30,
        title="Default editing steps",
        description="Diffusion step count used when an image editing request omits steps.",
    )

    edit_guidance: float = Field(
        default=2.5,
        title="Default editing guidance",
        description="Guidance strength used when an image editing request omits guidance.",
    )


settings_manager = SettingsManager(QwenSettings)
