"""Resolved MiniMax H3 generation parameters used by the model layer."""

from pydantic import BaseModel, Field


class GenerateParams(BaseModel):
    model: str = Field(description="Resolved model variant used for the run.")

    prompt: str = Field(description="Prompt used for the generation.")
    seed: int = Field(description="Resolved seed; generated when request seed is null.")
    width: int = Field(description="Resolved output width in pixels.")
    height: int = Field(description="Resolved output height in pixels.")
    num_frames: int = Field(description="Resolved output frame count at 24 fps.")
    steps: int = Field(description="Resolved denoising steps.")
    turbo: bool = Field(description="Whether the Turbo LoRA is applied.")
    fast: bool = Field(description="Whether mlx-serve's approximate speed-up is on.")
    use_video_audio: bool = Field(
        description="Whether reference video soundtracks are passed."
    )
    enhance_prompt: bool = Field(
        description="Whether the prompt is rewritten into the structured format."
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "steps": self.steps,
            "turbo": self.turbo,
            "fast": self.fast,
            "use_video_audio": self.use_video_audio,
            "enhance_prompt": self.enhance_prompt,
            "seed": self.seed,
        }
