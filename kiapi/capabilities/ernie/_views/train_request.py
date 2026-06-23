"""ERNIE-Image LoRA finetune request model. Always async (long-running).

The dataset is a ZIP uploaded to the Files API, with each image accompanied by a
same-stem ``.txt`` caption. The trained adapter is stored back in the Files API
and returned as the job's artifact (``adapter_file_id``).
"""

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef


class TrainRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant to finetune (see GET /v1/image/ernie/models). Omit for "
            "the default `turbo`."
        ),
    )
    dataset: FileRef = Field(
        description=(
            "Training dataset as a Files-API reference to a ZIP. Images may sit at "
            "the top level or in a single subfolder; each image needs a same-stem "
            "`.txt` caption (e.g. `cat.png` + `cat.txt`). `preview*` images are "
            "exempt from the caption requirement."
        ),
    )

    seed: int = Field(default=42, description="Random seed for the training run.")
    steps: int | None = Field(
        default=None,
        description=(
            "Inference/denoising steps used during training. Omit for the variant "
            "default (turbo 8, base 50)."
        ),
    )
    guidance: float | None = Field(
        default=None,
        description="Guidance scale. Omit for the variant default (turbo 1.0, base 4.0).",
    )
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
        description="Lower diffusion-timestep bound to sample. Omit for the default (1).",
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
        default=16, ge=1, description="Rank of the trained LoRA adapter."
    )
    lora_include_ff: bool = Field(
        default=False,
        description=(
            "Also train feed-forward / time-embedding layers (larger adapter), not "
            "just attention projections."
        ),
    )
    lora_layers: dict | None = Field(
        default=None,
        description=(
            "Advanced: explicit mflux LoRA target spec. Omit to use the built-in "
            "default targets derived from `lora_rank` / `lora_include_ff`."
        ),
    )
