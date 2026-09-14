"""The complete contract for one Ideogram 4 txt2img run.

Built from settings + request by ``resolve_generate_params``; the model needs
nothing else to produce the image and its metadata.
"""

from typing import Any, Literal

from pydantic import BaseModel


class GenerateParams(BaseModel):
    kind: Literal["txt2img"] = "txt2img"
    model: str

    prompt: str | dict[str, Any]
    preset: str

    seed: int
    width: int
    height: int
    quantize: int | None
    strict_caption_validation: bool
    warn_on_caption_issues: bool

    format: Literal["png", "jpeg", "webp"]
    quality: int
