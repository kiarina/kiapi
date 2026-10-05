"""MiniMax H3 video generation request model.

Text plus optional ordered references (images, videos, audio) → MP4 with
stereo audio. One endpoint serves both sync and async via ``mode``.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description="Model variant (see GET /v1/video/h3/models). Omit for the default.",
    )
    mode: Literal["sync", "async"] = Field(
        default="async",
        description=(
            "`async` (default) returns 202 with a job_id immediately — poll "
            "GET /v1/jobs/{job_id}. A run takes tens of minutes, so `sync` usually "
            "times out (504) while the job keeps running."
        ),
    )

    prompt: str = Field(
        ...,
        min_length=1,
        description=(
            "Description of the video and its sound. Refer to references as "
            "`<Picture N>`, `<Video N>` and `<Audio N>` (1-based per type, see the "
            "API description for the numbering). Write dialogue inside "
            "`<d>[Japanese] ...</d>`. The six-section format of the official guide "
            "gives the most faithful results."
        ),
        examples=[
            "The pink cat character from <Picture 1> waves at the camera and hops "
            "happily on a sunny park lawn."
        ],
    )
    images: list[FileRef] = Field(
        default_factory=list,
        max_length=9,
        description=(
            "Reference images, in `<Picture 1>`, `<Picture 2>`, ... order (at most 9). "
            "Use them for characters, objects, scenes, or styles."
        ),
    )
    videos: list[FileRef] = Field(
        default_factory=list,
        max_length=3,
        description=(
            "Reference videos, in `<Video 1>`, ... order (at most 3, each at least "
            "2 seconds). Each is cut to the generated length. Use them for setting, "
            "camera, motion, editing, or continuation."
        ),
    )
    use_video_audio: bool = Field(
        default=False,
        description=(
            "Also pass each reference video's soundtrack. Soundtracks take the first "
            "`<Audio N>` labels, in video order, before the standalone `audios`."
        ),
    )
    audios: list[FileRef] = Field(
        default_factory=list,
        max_length=3,
        description=(
            "Standalone reference audio clips (at most 3, at least 2 seconds; longer "
            "clips are cut to 15 seconds), for a voice timbre, music, or sound to "
            "reuse. Needs at least one image or video reference."
        ),
    )
    enhance_prompt: bool = Field(
        default=True,
        description=(
            "Rewrite the prompt into MiniMax's structured format before generation, "
            "with a kiapi chat model that sees the official prompt guide, the "
            "reference images, and frames of the reference videos (it cannot hear "
            "audio, so say in the prompt what each `<Audio N>` is for). Adds about "
            "2 minutes. Skipped when the prompt already uses the format. The result "
            "`params.enhanced_prompt` holds the text used."
        ),
    )
    width: int | None = Field(
        default=None,
        description=(
            "Output width in pixels. Omit for server default 960. Must be a positive "
            "multiple of 32; width * height may not exceed 1344 * 768."
        ),
    )
    height: int | None = Field(
        default=None,
        description=(
            "Output height in pixels. Omit for server default 544. Must be a positive "
            "multiple of 32."
        ),
    )
    num_frames: int | None = Field(
        default=None,
        description=(
            "Number of output frames at 24 fps. Omit for server default 124 (~5.2 s). "
            "Must satisfy `5 + 17*k` (for example 22, 56, 124, 243, 362)."
        ),
    )
    steps: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description=(
            "Denoising steps. Omit for 8 with `turbo` and 20 without it. Time grows "
            "linearly with steps."
        ),
    )
    turbo: bool = Field(
        default=True,
        description=(
            "Apply the LightX2V Ref2VA Turbo LoRA (8-step distillation). Disable for "
            "the base model at 20 steps, about 2.5x slower."
        ),
    )
    fast: bool = Field(
        default=False,
        description=(
            "mlx-serve's approximate speed-up (velocity caching and attention "
            "broadcast). Faster but lossy; off by default."
        ),
    )
    seed: int | None = Field(
        default=None,
        description=(
            "Random seed for reproducibility. Omit for a random seed (the resolved "
            "seed is recorded in the result `params`)."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "images": [ref.model_dump(mode="json") for ref in self.images],
            "videos": [ref.model_dump(mode="json") for ref in self.videos],
            "use_video_audio": self.use_video_audio,
            "audios": [ref.model_dump(mode="json") for ref in self.audios],
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "steps": self.steps,
            "enhance_prompt": self.enhance_prompt,
            "turbo": self.turbo,
            "fast": self.fast,
            "seed": self.seed,
        }
