"""ACE-Step extract request model."""

from pydantic import Field

from kiapi.core.file import FileRef

from .ace_step_base import AceStepBase


class ExtractRequest(AceStepBase):
    source: FileRef = Field(
        description=(
            "Source audio to separate (Files-API file id, http(s) URL, or data URL). "
            "POST the WAV to /v1/files first to get a file id."
        )
    )
    targets: list[str] = Field(
        default=["vocals", "drums", "bass", "other"],
        description=(
            "Stems to separate out, e.g. vocals / drums / bass / other (default: all "
            "four). Each target becomes one artifact (file_id) within the single job."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "source": self.source.model_dump(mode="json"),
            "targets": self.targets,
            "seed": self.seed,
            "inference_steps": self.inference_steps,
            "guidance_scale": self.guidance_scale,
            "shift": self.shift,
        }
