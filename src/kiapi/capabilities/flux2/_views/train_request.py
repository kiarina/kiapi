"""FLUX.2 LoRA finetune request model. Always async (long-running).

``training_mode`` selects between ``text`` (captioned images) and ``edit``
(``*_in`` / ``*_out`` image pairs with ``*_in.txt`` prompts). Only the base
variants (``klein-base-4b`` / ``klein-base-9b``) are trainable.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef


class TrainRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Base variant to finetune: `klein-base-4b` (default) or "
            "`klein-base-9b`. The distilled `klein-9b` is not trainable."
        ),
    )
    dataset: FileRef = Field(
        description=(
            "Training dataset as a Files-API reference to a ZIP. For "
            "`training_mode=text`: images with same-stem `.txt` captions "
            "(`cat.png` + `cat.txt`). For `training_mode=edit`: `*_in.*` / `*_out.*` "
            "image pairs with `*_in.txt` prompts."
        ),
    )
    training_mode: Literal["text", "edit"] = Field(
        default="text",
        description=(
            "`text` trains on captioned images; `edit` trains on in/out image pairs "
            "for editing-style adapters. Must match the dataset layout."
        ),
    )

    seed: int = Field(default=42, description="Random seed for the training run.")
    steps: int | None = Field(
        default=None,
        description=(
            "Inference/denoising steps used during training. Omit for the variant "
            "default (40)."
        ),
    )
    guidance: float = Field(default=1.0, description="Guidance scale during training.")
    quantize: int | None = Field(
        default=None,
        description=(
            "Quantization bits during training, one of {3, 4, 5, 6, 8}. Omit for "
            "the variant default (8)."
        ),
    )
    max_resolution: int | None = Field(
        default=512,
        description="Images are resized so their long side is at most this many pixels.",
    )
    low_ram: bool = Field(
        default=True,
        description="Trade speed for lower peak memory during training.",
    )

    num_epochs: int = Field(
        default=10, ge=1, description="Number of passes over the dataset."
    )
    batch_size: int = Field(default=1, ge=1, description="Training batch size.")
    timestep_low: int | None = Field(
        default=None,
        description="Lower diffusion-timestep bound to sample. Omit for the variant default (25).",
    )
    timestep_high: int | None = Field(
        default=None,
        description="Upper diffusion-timestep bound to sample. Omit to use `steps`.",
    )
    learning_rate: float = Field(default=1e-4, description="AdamW learning rate.")
    save_frequency: int | None = Field(
        default=None,
        description=(
            "Checkpoint every N steps. Omit to only keep the final checkpoint."
        ),
    )

    lora_rank: int = Field(
        default=8, ge=1, description="Rank of the trained LoRA adapter."
    )
    lora_include_ff: bool = Field(
        default=True,
        description=(
            "Also train feed-forward layers (larger adapter), not just attention "
            "projections."
        ),
    )
    lora_layers: dict | None = Field(
        default=None,
        description=(
            "Advanced: explicit mflux LoRA target spec. Omit to use the built-in "
            "default targets derived from `lora_rank` / `lora_include_ff`."
        ),
    )
