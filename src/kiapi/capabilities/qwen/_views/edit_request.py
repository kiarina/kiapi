"""Qwen Image edit request model. Natural-language single/multi-image editing.

One endpoint serves both sync and async via ``mode``. Takes one or more reference
``images`` plus a ``prompt``; defaults for ``width`` / ``height`` / ``steps`` /
``guidance`` / ``quantize`` are resolved server-side when omitted. A ``quantize``
override or any ``loras`` builds a one-off transient model (slower, not reused).
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
            "Model variant (see GET /v1/image/qwen/models). Omit for the default "
            "`edit-2509`; `/edit` only accepts `edit-2509` (use `/generate` for "
            "`image`)."
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
        description="Natural-language instruction describing the edit (required).",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="Optional text describing what to avoid in the result.",
    )
    images: list[FileRef] = Field(
        ...,
        min_length=1,
        description=(
            "One or more reference images (Files-API file ids, http(s) URLs, or data "
            "URLs) to edit / compose under the prompt. At least one is required."
        ),
    )

    width: int | None = Field(
        default=None,
        description=(
            "Output width in pixels. Omit for the server default (1024). Must be a "
            "multiple of 16 and at most 2048."
        ),
    )
    height: int | None = Field(
        default=None,
        description=(
            "Output height in pixels. Omit for the server default (1024). Must be a "
            "multiple of 16 and at most 2048."
        ),
    )
    steps: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Number of denoising steps (1..100). Omit for the server default (30). "
            "More steps = slower, sometimes higher quality."
        ),
    )
    guidance: float | None = Field(
        default=None,
        description=(
            "Classifier-free guidance scale. Omit for the server default (2.5); "
            "higher follows the prompt more strictly."
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
            "model's quantization (q8). A differing value builds a one-off transient "
            "model (slower, not reused)."
        ),
    )
    scheduler: str = Field(
        default="linear",
        description="Noise scheduler. `linear` is the default and tested value.",
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
            "images": [image.model_dump(mode="json") for image in self.images],
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
