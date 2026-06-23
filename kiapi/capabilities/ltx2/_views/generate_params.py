"""Resolved LTX-2 generation parameters used by the model layer."""

from pydantic import BaseModel, Field


class GenerateParams(BaseModel):
    model: str = Field(description="Resolved model variant used for the run.")

    prompt: str = Field(description="Prompt used for the generation.")
    seed: int = Field(description="Resolved seed; generated when request seed is null.")
    width: int = Field(description="Resolved output width in pixels.")
    height: int = Field(description="Resolved output height in pixels.")
    num_frames: int = Field(description="Resolved output frame count.")
    fps: int = Field(description="Resolved output frame rate.")
    image_strength: float = Field(description="Resolved first-frame strength.")
    end_image_strength: float | None = Field(
        description="Resolved last-frame strength, or null when omitted."
    )
    generate_audio: bool = Field(
        description="Whether LTX-2 should synthesize synchronized audio."
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "fps": self.fps,
            "seed": self.seed,
            "image_strength": self.image_strength,
            "end_image_strength": self.end_image_strength,
            "generate_audio": self.generate_audio,
        }
