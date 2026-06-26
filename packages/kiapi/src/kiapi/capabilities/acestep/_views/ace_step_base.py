"""Shared ACE-Step request fields (preset, mode, sampling overrides).

Every acestep operation (generate/cover/repaint/extract) inherits these. The
sampling overrides default to ``None`` so the chosen preset supplies its tuned
value; set them only to deviate from the preset.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AceStepBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(
        default="xl-base",
        pattern="^(xl-base|turbo)$",
        description=(
            "Preset (see GET /v1/audio/acestep/models). `xl-base` (default) = highest "
            "quality (32 steps, CFG 7.0). `turbo` = fastest (8 steps, no CFG), good for "
            "prototyping."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the track (504 on timeout); `async` returns 202 with a "
            "job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )
    seed: int = Field(
        default=-1,
        description=(
            "Random seed for reproducibility. `-1` picks a random seed; the same seed "
            "with the same params reproduces the output. The resolved seed is recorded "
            "in the result `params`."
        ),
    )
    inference_steps: int | None = Field(
        default=None,
        description=(
            "Override the preset's denoising step count (xl-base 32 / turbo 8). More "
            "steps = higher quality, slower. Omit to use the preset default."
        ),
    )
    guidance_scale: float | None = Field(
        default=None,
        description=(
            "Override classifier-free guidance strength (xl-base default 7.0). Higher "
            "follows the prompt more strictly. Ignored by `turbo`, which runs without "
            "CFG. Omit to use the preset default."
        ),
    )
    shift: float | None = Field(
        default=None,
        description=(
            "Override the timestep schedule shift. 3.0 is correct; values near 1.0 "
            "produce noisy output. Omit to use the preset default."
        ),
    )
