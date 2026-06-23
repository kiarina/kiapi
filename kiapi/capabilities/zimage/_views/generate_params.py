"""Resolved Z-Image generation parameters passed to the model layer."""

from typing import Literal

from pydantic import BaseModel

from .._schemas.lora_ref import LoraRef


class GenerateParams(BaseModel):
    model: str
    prompt: str
    negative_prompt: str | None
    seed: int
    width: int
    height: int
    steps: int
    guidance: float | None
    quantize: int | None
    format: Literal["png", "jpeg", "webp"]
    quality: int
    loras: list[LoraRef]
    mode: Literal["txt2img"] = "txt2img"
