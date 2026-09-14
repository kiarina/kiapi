"""Ideogram 4 text-to-image request model.

One endpoint serves both sync and async via ``mode``. Ideogram 4 is typography-
focused txt2img: a structured JSON caption (`prompt`) gives the best results,
though plain text is accepted. A ``quantize`` override builds a one-off transient
model (slower, not reused); otherwise the resident model is used.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant (see GET /v1/image/ideogram4/models). Only `fp8` exists; "
            "omit to use it. Aliases `ideogram4` / `ideogram-4` are accepted."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the image (504 on timeout); `async` returns 202 with "
            "a job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )

    # Ideogram 4 works best with a structured JSON caption, but mflux also
    # accepts plain text prompts. Keep both forms available to callers.
    prompt: str | dict[str, Any] = Field(
        ...,
        description=(
            "What to generate. Prefer a structured JSON caption with "
            "`high_level_description`, optional `style_description`, and "
            "`compositional_deconstruction` (`background` + `elements`, each with "
            "`type` text|obj, `bbox` [x1,y1,x2,y2] in 0-1000 layout coords, `text` "
            "for text elements, and `desc`). Plain text is accepted but usually "
            "weaker for typography. Must not be empty."
        ),
    )
    preset: Literal["V4_DEFAULT_20", "V4_QUALITY_48", "V4_TURBO_12"] = Field(
        default="V4_DEFAULT_20",
        description=(
            "Sampler preset bundling steps, guidance schedule, and noise schedule. "
            "`V4_TURBO_12` is fastest (12 steps), `V4_DEFAULT_20` is balanced, "
            "`V4_QUALITY_48` is highest quality and slowest (48 steps)."
        ),
    )

    width: int | None = Field(
        default=None,
        description=(
            "Output width in pixels. Omit for the server default (1024). Must be a "
            "multiple of 16 and within 256..2048."
        ),
    )
    height: int | None = Field(
        default=None,
        description=(
            "Output height in pixels. Omit for the server default (1024). Must be a "
            "multiple of 16 and within 256..2048."
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
            "model's quantization. A differing value builds a one-off transient "
            "model (slower, not reused)."
        ),
    )
    strict_caption_validation: bool = Field(
        default=False,
        description=(
            "If true, fail the request (400) when mflux reports JSON-caption schema "
            "warnings instead of proceeding."
        ),
    )
    warn_on_caption_issues: bool = Field(
        default=True,
        description="Ask mflux to surface warnings about JSON-caption schema issues.",
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
            "prompt": self.prompt,
            "preset": self.preset,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "quantize": self.quantize,
            "strict_caption_validation": self.strict_caption_validation,
            "warn_on_caption_issues": self.warn_on_caption_issues,
            "format": self.format,
            "quality": self.quality,
        }
