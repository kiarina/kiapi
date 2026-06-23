"""The complete contract for one FLUX.2 LoRA finetune run.

Built from settings + request by ``resolve_train_params``; combined with the
resolved model spec and the on-disk dataset/output dirs, the model needs neither
settings nor request to assemble its training config.
"""

from typing import Literal

from pydantic import BaseModel


class TrainParams(BaseModel):
    training_mode: Literal["text", "edit"]

    seed: int
    steps: int
    guidance: float
    quantize: int | None
    max_resolution: int | None
    low_ram: bool

    num_epochs: int
    batch_size: int
    timestep_low: int
    timestep_high: int
    learning_rate: float
    save_frequency: int

    lora_rank: int
    lora_include_ff: bool
    lora_layers: dict | None
