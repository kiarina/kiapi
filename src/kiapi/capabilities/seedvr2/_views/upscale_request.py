"""SeedVR2 upscale request model.

Image → upscaled image (diffusion super-resolution). One endpoint serves both
sync and async via ``mode``. The input image is referenced by ``image``
(FileRef). A ``quantize`` override runs a one-off transient model; otherwise the
resident model is used.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef


class UpscaleRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant (see GET /v1/image/seedvr2/models). Omit for the "
            "default `3b`; `7b` is the larger, higher-quality variant. Aliases "
            "`seedvr2-3b` / `seedvr2-7b` are also accepted."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the image (504 on timeout); `async` returns 202 with "
            "a job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )

    image: FileRef = Field(
        ...,
        description=(
            "Input image to upscale (Files-API file id, http(s) URL, or data URL)."
        ),
    )
    resolution: int | str = Field(
        default="2x",
        description=(
            "Target size: an integer shortest-edge pixel target (16..2048), or a "
            "scale factor string like `2x` / `1.5x` (> 0 and at most 4.0x). "
            "Default `2x`."
        ),
    )
    softness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Detail smoothing in 0..1. 0 keeps maximum sharpness; higher values "
            "soften the result. Default 0.0."
        ),
    )
    seed: int | None = Field(
        default=None,
        description=(
            "Random seed for reproducibility. Omit for a random seed (the resolved "
            "seed is recorded in the result `params`)."
        ),
    )
    quantize: int | None = Field(
        default=None,
        description=(
            "Quantization bits, one of {3, 4, 5, 6, 8}. Omit to use the resident "
            "model's quantization (q8). A differing value builds a one-off "
            "transient model (slower, not reused)."
        ),
    )

    format: Literal["png", "jpeg", "webp"] = Field(
        default="png",
        description="Output image encoding for the produced file.",
    )
    quality: int = Field(
        default=90,
        ge=1,
        le=100,
        description="Encoder quality 1..100 (used for jpeg/webp; ignored for png).",
    )

    def gen_params(self) -> dict:
        return {
            "image": self.image.model_dump(mode="json"),
            "resolution": self.resolution,
            "softness": self.softness,
            "seed": self.seed,
            "quantize": self.quantize,
            "format": self.format,
            "quality": self.quality,
        }
