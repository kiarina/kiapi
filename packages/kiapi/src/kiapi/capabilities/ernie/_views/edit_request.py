"""ERNIE-Image single-image edit (img2img) request model.

Same shape as the generate request plus an input ``image`` (FileRef) and
``image_strength``. By default the output must be square (mflux 0.18.0 can fail
on some non-square ERNIE img2img sizes); the guard is overrideable server-side.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef

from .._schemas.lora_ref import LoraRef


class EditRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant (see GET /v1/image/ernie/models). Omit for the default "
            "`turbo`; `base` is higher-quality but slower. Aliases such as "
            "`ernie-image-turbo` / `ernie-image` are accepted."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the image (504 on timeout); `async` returns 202 with "
            "a job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )

    prompt: str = Field(
        ...,
        min_length=1,
        description="Text prompt describing the desired edit (required).",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="Optional text describing what to avoid in the result.",
    )
    image: FileRef = Field(
        description=(
            "Input image to edit, as a Files-API file id, http(s) URL, or data URL."
        ),
    )
    image_strength: float = Field(
        default=0.4,
        description=(
            "How much the input image is preserved, in 0..1. Lower keeps more of "
            "the input; higher follows the prompt more freely."
        ),
    )

    width: int | None = Field(
        default=None,
        description=(
            "Output width in pixels. Omit for the server default (1024). Must be a "
            "multiple of 16 and at most 2048. By default must equal height (square)."
        ),
    )
    height: int | None = Field(
        default=None,
        description=(
            "Output height in pixels. Omit for the server default (1024). Must be a "
            "multiple of 16 and at most 2048. By default must equal width (square)."
        ),
    )
    steps: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Number of denoising steps (1..100). Omit for the variant default "
            "(turbo 8, base 50)."
        ),
    )
    guidance: float | None = Field(
        default=None,
        description=(
            "Classifier-free guidance scale. Omit for the variant default "
            "(turbo 1.0, base 4.0); higher follows the prompt more strictly."
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
            "model's quantization (default 8). A differing value builds a one-off "
            "transient model (slower, not reused)."
        ),
    )
    scheduler: str = Field(
        default="linear",
        description="Noise scheduler. `linear` is the default and only tested value.",
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

    loras: list[LoraRef] = Field(
        default_factory=list,
        description=(
            "Up to 4 LoRA adapters [{file, scale}] referencing Files-API ids. Any "
            "lora forces a one-off transient model (slower, not reused)."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "image": self.image.model_dump(mode="json"),
            "image_strength": self.image_strength,
            "width": self.width,
            "height": self.height,
            "steps": self.steps,
            "guidance": self.guidance,
            "seed": self.seed,
            "quantize": self.quantize,
            "scheduler": self.scheduler,
            "format": self.format,
            "quality": self.quality,
            "loras": [lr.model_dump() for lr in self.loras],
        }
