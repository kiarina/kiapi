"""ERNIE-Image capability defaults + caps, read from ``KIAPI_ERNIE_`` env vars."""

from typing import cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class ErnieSettings(BaseSettings):
    """Settings for ERNIE-Image model variants, generation/edit defaults, and LoRA training."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_ERNIE_",
        extra="ignore",
        protected_namespaces=(),
    )

    turbo_model: str = Field(
        default="baidu/ERNIE-Image-Turbo",
        title="Turbo model repo",
        description="Hugging Face repo ID used as the ERNIE-Image turbo variant.",
    )

    base_model: str = Field(
        default="baidu/ERNIE-Image",
        title="Base model repo",
        description="Hugging Face repo ID used as the ERNIE-Image base variant.",
    )

    default_steps: dict[str, int] = Field(
        default_factory=lambda: {"turbo": 8, "base": 50},
        title="Default steps by variant",
        description=(
            "Diffusion step count used when a generation or edit request omits steps.\n"
            "Keys are variant names such as turbo or base; values are step counts."
        ),
    )

    default_guidance: dict[str, float] = Field(
        default_factory=lambda: {"turbo": 1.0, "base": 4.0},
        title="Default guidance by variant",
        description=(
            "Guidance strength used when a generation or edit request omits guidance.\n"
            "Keys are variant names; values are guidance values."
        ),
    )

    default_quantize: dict[str, int | None] = Field(
        default_factory=lambda: cast(dict[str, int | None], {"turbo": 8, "base": 8}),
        title="Default quantization bits by variant",
        description=(
            "Default quantization bit count used when loading a model.\n"
            "Keys are variant names; values are bit counts such as 8, or None "
            "for no quantization."
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

    # --------------------------------------------------
    # edit
    # --------------------------------------------------

    edit_require_square: bool = Field(
        default=True,
        title="Require square edit input",
        description=(
            "When true, ERNIE image-to-image/edit avoids non-square sizes.\n"
            "This conservative default works around mflux VAE latent-packing constraints."
        ),
    )

    # --------------------------------------------------
    # train
    # --------------------------------------------------

    train_reserve_gb: float = Field(
        default=24.0,
        title="LoRA training reserved memory GB",
        description="Memory in GB reserved for the runtime peak of an ERNIE-Image LoRA training job.",
    )

    train_steps: dict[str, int] = Field(
        default_factory=lambda: {"turbo": 8, "base": 50},
        title="Training steps by variant",
        description=(
            "Step count used when a LoRA training request omits steps.\n"
            "Keys are variant names; values are training step counts."
        ),
    )

    train_timestep_low: dict[str, int] = Field(
        default_factory=lambda: {"turbo": 1, "base": 1},
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


settings_manager = SettingsManager(ErnieSettings)
