"""Resolved Z-Image LoRA finetune parameters passed to the model layer."""

from pydantic import BaseModel


class TrainParams(BaseModel):
    model: str
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
