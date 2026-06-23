"""The complete contract for one ERNIE-Image txt2img run.

Built from settings + request by ``resolve_generate_params``; the model needs
nothing else to produce the image and its metadata.
"""

from typing import Literal

from pydantic import BaseModel

from .._schemas.lora_ref import LoraRef


class GenerateParams(BaseModel):
    kind: Literal["txt2img"] = "txt2img"
    model: str

    prompt: str
    negative_prompt: str | None

    seed: int
    width: int
    height: int
    steps: int
    guidance: float
    quantize: int | None
    scheduler: str

    format: Literal["png", "jpeg", "webp"]
    quality: int

    loras: list[LoraRef]
