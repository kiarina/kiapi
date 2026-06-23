"""ACE-Step cover request model."""

from pydantic import Field

from kiapi.core.file import FileRef

from .ace_step_base import AceStepBase


class CoverRequest(AceStepBase):
    source: FileRef = Field(
        description=(
            "Source audio to re-style (Files-API file id, http(s) URL, or data URL). "
            "POST the WAV to /v1/files first to get a file id."
        )
    )
    prompt: str = Field(
        description=(
            "Target style description for the cover — the SOUND to move toward "
            "(genre, instruments, mood, production)."
        )
    )
    strength: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description=(
            "How closely to follow the source structure, in 0..1. 0 = free / more "
            "creative, 1 = strict / more faithful. 0.7 preserves structure well."
        ),
    )
    duration: int | None = Field(
        default=None,
        ge=5,
        le=300,
        description="Output length in seconds (5-300). Omit to match the source length.",
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "source": self.source.model_dump(mode="json"),
            "strength": self.strength,
            "duration": self.duration,
            "seed": self.seed,
            "inference_steps": self.inference_steps,
            "guidance_scale": self.guidance_scale,
            "shift": self.shift,
        }
