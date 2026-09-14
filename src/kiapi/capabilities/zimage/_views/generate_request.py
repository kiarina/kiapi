"""Z-Image text-to-image request model.

One endpoint serves both sync and async via ``mode``. Defaults for ``steps`` /
``guidance`` / ``quantize`` are variant-dependent (turbo vs base) and resolved
server-side when omitted. A ``quantize`` override or any ``loras`` builds a
one-off transient model (slower, not reused).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .._schemas.lora_ref import LoraRef


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant (see GET /v1/image/zimage/models). Omit for the default "
            "`turbo` (distilled, few-step, fast); `base` is the full, higher-quality, "
            "slower variant."
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
        description="Text prompt describing the image to generate (required).",
    )
    negative_prompt: str | None = Field(
        default=None,
        description=(
            "Optional text describing what to avoid in the image. Most effective on "
            "`base` with guidance > 1; `turbo` is distilled (no guidance) so it has "
            "little effect there."
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
            "(turbo 9, base 28). More steps = slower, sometimes higher quality."
        ),
    )
    guidance: float | None = Field(
        default=None,
        description=(
            "Classifier-free guidance scale. Omit for the variant default "
            "(turbo: none — distilled; base: 4.0). Higher follows the prompt more "
            "strictly."
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
            "model's quantization (turbo is pre-quantized 4-bit; base defaults to 8). "
            "A differing value builds a one-off transient model (slower, not reused)."
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
            "negative_prompt": self.negative_prompt,
            "width": self.width,
            "height": self.height,
            "steps": self.steps,
            "guidance": self.guidance,
            "seed": self.seed,
            "quantize": self.quantize,
            "format": self.format,
            "quality": self.quality,
            "loras": [lr.model_dump() for lr in self.loras],
        }
