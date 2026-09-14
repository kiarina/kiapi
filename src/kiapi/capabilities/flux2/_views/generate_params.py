"""The complete contract for one FLUX.2 generate run (txt2img or img2img).

Built from settings + request by ``resolve_generate_params``; the model needs
nothing else to produce the image and its metadata. ``init_image_path`` is the
locally resolved input file (img2img only), kept out of the recorded metadata in
favour of ``init_image_file_id``.
"""

from typing import Literal

from pydantic import BaseModel

from .._schemas.lora_ref import LoraRef


class GenerateParams(BaseModel):
    kind: Literal["txt2img", "img2img"]
    model: str

    prompt: str
    init_image_file_id: str | None
    init_image_path: str | None
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
