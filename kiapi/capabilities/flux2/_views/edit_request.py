"""FLUX.2 multi-reference image edit request model.

Edits/combines one or more reference ``images`` under a ``prompt``. Same shape as
the generate request except the input is a list of reference images instead of an
optional ``init_image``. Defaults for ``steps`` / ``guidance`` / ``quantize`` are
variant-dependent and resolved server-side when omitted.
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
            "Model variant (see GET /v1/image/flux2/models). Omit for the default "
            "`klein-9b`; `klein-base-4b` / `klein-base-9b` are the slower base "
            "variants. Aliases such as `flux2-klein-9b` are accepted."
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
    images: list[FileRef] = Field(
        ...,
        min_length=1,
        description=(
            "One or more reference images to edit/combine, each a Files-API file "
            "id, http(s) URL, or data URL. Multi-reference editing draws on all of "
            "them."
        ),
    )
    image_strength: float | None = Field(
        default=None,
        description=(
            "How much the reference images are preserved, in 0..1. Lower keeps more "
            "of the input; higher follows the prompt more freely."
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
            "Number of denoising steps (1..100). Omit for the variant default "
            "(klein-9b 4, base variants 40)."
        ),
    )
    guidance: float | None = Field(
        default=None,
        description=(
            "Classifier-free guidance scale. Omit for the variant default (1.0); "
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
            "model's quantization (klein-9b unquantized, base variants q8). A "
            "differing value builds a one-off transient model (slower, not reused)."
        ),
    )
    scheduler: str = Field(
        default="flow_match_euler_discrete",
        description=(
            "Noise scheduler. `flow_match_euler_discrete` is the default and only "
            "tested value."
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
            "images": [image.model_dump(mode="json") for image in self.images],
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
