"""The complete contract for one FLUX.2 multi-reference edit run.

Built from settings + request by ``resolve_edit_params``; the model needs nothing
else to produce the image and its metadata. ``image_paths`` are the locally
resolved input files, kept out of the recorded metadata in favour of
``image_file_ids``.
"""

from typing import Literal

from pydantic import BaseModel

from .._schemas.lora_ref import LoraRef


class EditParams(BaseModel):
    kind: Literal["edit"] = "edit"
    model: str

    prompt: str
    image_file_ids: list[str]
    image_paths: list[str]
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
