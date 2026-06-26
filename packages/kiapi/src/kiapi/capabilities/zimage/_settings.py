"""Image (zimage) capability defaults + caps, read from ``KIAPI_ZIMAGE_``."""

from typing import cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class ZimageSettings(BaseSettings):
    """Settings for Z-Image model variants, generation defaults, and LoRA training defaults."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_ZIMAGE_",
        extra="ignore",
        protected_namespaces=(),
    )

    turbo_repo: str = Field(
        default="filipstrand/Z-Image-Turbo-mflux-4bit",
        title="Turbo model repo",
        description="Hugging Face repo ID used as the Z-Image turbo variant.",
    )

    base_repo: str = Field(
        default="Tongyi-MAI/Z-Image",
        title="Base model repo",
        description="Hugging Face repo ID used as the Z-Image base variant.",
    )

    default_quantize: dict[str, int | None] = Field(
        default_factory=lambda: {"turbo": None, "base": 8},
        title="Default quantization bits by variant",
        description=(
            "Default quantization bit count used when loading a generation model.\n"
            "Keys are variant names; values are bit counts such as 8, or None "
            "for no quantization."
        ),
    )

    # --------------------------------------------------
    # generate
    # --------------------------------------------------

    default_steps: dict[str, int] = Field(
        default_factory=lambda: {"turbo": 9, "base": 28},
        title="Default steps by variant",
        description=(
            "Diffusion step count used when a generation request omits steps.\n"
            "Keys are variant names such as turbo or base; values are step counts."
        ),
    )

    default_guidance: dict[str, float | None] = Field(
        default_factory=lambda: {"turbo": None, "base": 4.0},
        title="Default guidance by variant",
        description=(
            "Guidance strength used when a generation request omits guidance.\n"
            "Keys are variant names; values are guidance values. None uses the "
            "model default."
        ),
    )

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
        description="Maximum number of LoRA adapters that can be applied in one generation request.",
    )

    # --------------------------------------------------
    # train
    # --------------------------------------------------

    train_reserve_gb: float = Field(
        default=24.0,
        title="LoRA training reserved memory GB",
        description="Memory in GB reserved for the runtime peak of a Z-Image LoRA training job.",
    )

    train_steps: dict[str, int] = Field(
        default_factory=lambda: {"turbo": 9, "base": 20},
        title="Training steps by variant",
        description=(
            "Step count used when a LoRA training request omits steps.\n"
            "Keys are variant names; values are training step counts."
        ),
    )

    train_timestep_low: dict[str, int] = Field(
        default_factory=lambda: {"turbo": 4, "base": 0},
        title="Training timestep lower bound by variant",
        description=(
            "Lower bound of the timestep range used during LoRA training.\n"
            "Keys are variant names; values are lower-bound timestep values."
        ),
    )

    train_quantize: dict[str, int | None] = Field(
        default_factory=lambda: cast(dict[str, int | None], {"turbo": 8, "base": 8}),
        title="Training quantization bits by variant",
        description=(
            "Quantization bit count applied to the model during LoRA training.\n"
            "Keys are variant names; values are bit counts such as 8, or None "
            "for no quantization."
        ),
    )

    train_default_epochs: int = Field(
        default=10,
        title="Default LoRA training epochs",
        description="Epoch count used when a LoRA training request omits epochs.",
    )

    train_default_rank: int = Field(
        default=16,
        title="Default LoRA training rank",
        description=(
            "LoRA rank used when a LoRA training request omits rank.\n"
            "Higher values increase expressiveness and memory usage."
        ),
    )

    train_default_lr: float = Field(
        default=1e-4,
        title="Default LoRA training learning rate",
        description="Learning rate used when a LoRA training request omits lr.",
    )

    train_max_epochs: int = Field(
        default=1000,
        title="Maximum LoRA training epochs",
        description="Upper limit for epochs accepted in a LoRA training request.",
    )


settings_manager = SettingsManager(ZimageSettings)
