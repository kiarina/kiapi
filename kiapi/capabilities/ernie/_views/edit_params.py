"""The complete contract for one ERNIE-Image single-image edit (img2img) run.

Built from settings + request by ``resolve_edit_params``; the model needs nothing
else to produce the image and its metadata. ``image_path`` is the locally resolved
input file, kept out of the recorded metadata in favour of ``image_file_id``.
"""

from typing import Literal

from pydantic import BaseModel

from .._schemas.lora_ref import LoraRef


class EditParams(BaseModel):
    kind: Literal["edit"] = "edit"
    model: str

    prompt: str
    negative_prompt: str | None
    image_file_id: str
    image_path: str
    image_strength: float

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
