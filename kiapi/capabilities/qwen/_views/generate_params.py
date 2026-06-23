"""The complete contract for one Qwen Image generate run.

Built from settings + request by ``resolve_generate_params``; the model needs
nothing else to produce the image and its metadata. ``kind`` is ``img2img`` when
``image_path`` is set (resolved from ``init_image_file_id``), else ``txt2img``;
``image_path`` is kept out of the recorded metadata in favour of the file id.
"""

from typing import Literal

from pydantic import BaseModel

from .._schemas.lora_ref import LoraRef


class GenerateParams(BaseModel):
    kind: Literal["txt2img", "img2img"]
    model: str

    prompt: str
    negative_prompt: str | None
    init_image_file_id: str | None
    image_path: str | None
    image_strength: float | None

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
