"""AudioGen generate request model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "AudioGen variant to use. Omit/null to use the family default "
            "(`medium`). `medium` is currently the only built-in variant; discover "
            "available variants at GET /v1/audio/audiogen/models."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the WAV (504 on timeout); `async` returns 202 with a "
            "job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )

    prompt: str = Field(
        ...,
        min_length=1,
        examples=["heavy rain on a tin roof, distant thunder"],
        description=(
            "Sound-effect prompt. Concrete, audible descriptors work best: source, "
            "surface, distance, room/space, intensity, and ambience. This is for "
            "non-musical audio events; use `/v1/audio/acestep/generate` for music."
        ),
    )
    duration: float = Field(
        default=5.0,
        gt=0.0,
        description=(
            "Requested clip length in seconds. Must be > 0 and is also capped "
            "server-side by `KIAPI_AUDIOGEN_MAX_DURATION` (default 10.0 seconds)."
        ),
    )
    seed: int | None = Field(
        default=None,
        description=(
            "Random seed for reproducibility. Null picks a random seed; the resolved "
            "seed is recorded in the result `params`."
        ),
    )
    top_k: int = Field(
        default=250,
        ge=0,
        description=(
            "Top-k sampling limit. Keeps only the most likely k tokens. Set 0 to "
            "disable top-k; ignored when `top_p` is greater than 0."
        ),
    )
    top_p: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Nucleus sampling threshold. 0 disables nucleus sampling and uses "
            "`top_k`; values greater than 0 override `top_k`."
        ),
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        description=(
            "Sampling temperature. Lower values are more conservative; higher values "
            "increase variety and risk."
        ),
    )
    cfg_coef: float = Field(
        default=3.0,
        ge=0.0,
        description=(
            "Classifier-free guidance strength. Higher values follow the prompt more "
            "strictly; lower values allow more ambient variation."
        ),
    )

    def gen_params(self) -> dict:
        """Generation knobs (excludes routing fields like model/mode)."""
        return {
            "prompt": self.prompt,
            "duration": self.duration,
            "seed": self.seed,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "cfg_coef": self.cfg_coef,
        }
