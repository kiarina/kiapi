"""ACE-Step repaint request model."""

from pydantic import Field

from kiapi.core.file import FileRef

from .ace_step_base import AceStepBase


class RepaintRequest(AceStepBase):
    source: FileRef = Field(
        description=(
            "Source audio to repaint (Files-API file id, http(s) URL, or data URL). "
            "POST the WAV to /v1/files first to get a file id."
        )
    )
    prompt: str = Field(
        description="Style description for the repainted section (the SOUND to apply)."
    )
    start: float = Field(
        description="Start of the section to regenerate, in seconds from the track start."
    )
    end: float = Field(
        default=-1,
        description=(
            "End of the section, in seconds. `-1` repaints from `start` to the end of "
            "the track."
        ),
    )
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "How aggressively to regenerate the section, in 0..1. 0 = subtle, blends "
            "into the rest; 1 = aggressive."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "source": self.source.model_dump(mode="json"),
            "start": self.start,
            "end": self.end,
            "strength": self.strength,
            "seed": self.seed,
            "inference_steps": self.inference_steps,
            "guidance_scale": self.guidance_scale,
            "shift": self.shift,
        }
