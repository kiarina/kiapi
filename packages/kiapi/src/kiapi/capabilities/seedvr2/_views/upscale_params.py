"""The complete contract for one SeedVR2 image upscale run.

Built from settings + request by ``resolve_upscale_params``; the model needs
nothing else to produce the image and its metadata. ``image_path`` is the locally
resolved input file, kept out of the recorded metadata in favour of
``image_file_id``. ``resolution`` keeps the request value (an int shortest-edge
target or a scale like ``"2x"``); the model layer parses the scale form.
"""

from typing import Literal

from pydantic import BaseModel


class UpscaleParams(BaseModel):
    kind: Literal["upscale"] = "upscale"
    model: str

    image_file_id: str
    image_path: str
    resolution: int | str
    softness: float
    seed: int
    quantize: int | None

    format: Literal["png", "jpeg", "webp"]
    quality: int
