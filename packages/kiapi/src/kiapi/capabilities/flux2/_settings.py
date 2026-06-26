"""FLUX.2 capability defaults + caps, read from ``KIAPI_FLUX2_`` env vars."""

from typing import cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings_manager import SettingsManager


class Flux2Settings(BaseSettings):
    """Settings for FLUX.2 model variants, generation defaults, and LoRA training."""

    model_config = SettingsConfigDict(
        env_prefix="KIAPI_FLUX2_",
        extra="ignore",
        protected_namespaces=(),
    )

    klein_9b_model: str = Field(
        default="flux2-klein-9b",
        title="Klein 9B model name",
        description="Name registered in the model registry for the FLUX.2 Klein 9B variant.",
    )

    klein_base_4b_model: str = Field(
        default="flux2-klein-base-4b",
        title="Klein Base 4B model name",
        description="Name registered in the model registry for the FLUX.2 Klein Base 4B variant.",
    )

    klein_base_9b_model: str = Field(
        default="flux2-klein-base-9b",
        title="Klein Base 9B model name",
        description="Name registered in the model registry for the FLUX.2 Klein Base 9B variant.",
    )

    # --------------------------------------------------
    # generate
    # --------------------------------------------------

    default_steps: dict[str, int] = Field(
        default_factory=lambda: {
            "klein-9b": 4,
            "klein-base-4b": 40,
            "klein-base-9b": 40,
        },
        title="Default steps by variant",
        description=(
            "Diffusion step count used when a generation or edit request omits steps.\n"
            "Keys are variant names such as klein-9b; values are step counts."
        ),
    )

    default_guidance: dict[str, float] = Field(
        default_factory=lambda: {
            "klein-9b": 1.0,
            "klein-base-4b": 1.0,
            "klein-base-9b": 1.0,
        },
        title="Default guidance by variant",
        description=(
            "Guidance strength used when a generation or edit request omits guidance.\n"
            "Keys are variant names; values are guidance values."
        ),
    )

    default_quantize: dict[str, int | None] = Field(
        default_factory=lambda: cast(
            dict[str, int | None],
            {
                "klein-9b": None,
                "klein-base-4b": 8,
                "klein-base-9b": 8,
            },
        ),
        title="Default quantization bits by variant",
        description=(
            "Default quantization bit count used when loading a model.\n"
            "Keys are variant names; values are bit counts such as 8, or None "
            "for no quantization."
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
        description="Maximum number of LoRA adapters that can be applied in one generation or edit request.",
    )

    # --------------------------------------------------
    # train
    # --------------------------------------------------

    train_default_model: str = Field(
        default="klein-base-4b",
        title="Default LoRA training model",
        description=(
            "FLUX.2 variant name used when a LoRA training request omits model.\n"
            "Usually this should be a training-capable variant such as "
            "klein-base-4b or klein-base-9b."
        ),
    )

    train_reserve_gb: float = Field(
        default=24.0,
        title="LoRA training reserved memory GB",
        description="Memory in GB reserved for the runtime peak of a FLUX.2 LoRA training job.",
    )

    train_steps: dict[str, int] = Field(
        default_factory=lambda: {
            "klein-base-4b": 40,
            "klein-base-9b": 40,
        },
        title="Training steps by variant",
        description=(
            "Step count used when a LoRA training request omits steps.\n"
            "Keys are variant names; values are training step counts."
        ),
    )

    train_timestep_low: dict[str, int] = Field(
        default_factory=lambda: {
            "klein-base-4b": 25,
            "klein-base-9b": 25,
        },
        title="Training timestep lower bound by variant",
        description=(
            "Lower bound of the timestep range used during LoRA training.\n"
            "Keys are variant names; values are lower-bound timestep values."
        ),
    )

    train_quantize: dict[str, int | None] = Field(
        default_factory=lambda: cast(
            dict[str, int | None],
            {
                "klein-base-4b": 8,
                "klein-base-9b": 8,
            },
        ),
        title="Training quantization bits by variant",
        description=(
            "Quantization bit count applied to the model during LoRA training.\n"
            "Keys are variant names; values are bit counts such as 8, or None "
            "for no quantization."
        ),
    )


settings_manager = SettingsManager(Flux2Settings)
