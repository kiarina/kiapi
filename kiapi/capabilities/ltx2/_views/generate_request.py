"""LTX-2 video generation request model.

Text/image/audio → MP4. One endpoint serves both sync and async via ``mode``.
The generation mode (T2V, I2V, A2V, etc.) is inferred from which FileRef inputs
are present, not from a user-supplied mode field.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant (see GET /v1/video/ltx2/models). Omit for the "
            "default `distilled`; this is currently the only public variant."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the MP4 (504 on timeout); `async` returns 202 with "
            "a job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )

    prompt: str = Field(
        ...,
        min_length=1,
        description=(
            "Text description of the desired video. Distilled LTX-2 has no "
            "negative guidance, so describe the motion, subject, framing, and "
            "visual qualities you want rather than what to avoid."
        ),
        examples=["a cat walking through tall grass, sunny daylight, gentle camera"],
    )
    image: FileRef | None = Field(
        default=None,
        description=(
            "Optional first-frame conditioning image (Files-API file id, http(s) "
            "URL, or data URL). Present with no audio => I2V; present with audio "
            "=> A2V+I2V."
        ),
    )
    end_image: FileRef | None = Field(
        default=None,
        description=(
            "Optional last-frame conditioning image. Use with `image` for a "
            "first+last-frame transition, or alone for last-frame conditioning."
        ),
    )
    audio: FileRef | None = Field(
        default=None,
        description=(
            "Optional driving audio file (Files-API file id, http(s) URL, or data "
            "URL). When present, the mode becomes A2V and the audio is muxed into "
            "the output MP4. Mutually exclusive with `generate_audio=true`."
        ),
    )
    width: int | None = Field(
        default=None,
        description=(
            "Output width in pixels. Omit for server default 512. Must be a "
            "positive multiple of 64 and no greater than the configured cap "
            "(default 768)."
        ),
    )
    height: int | None = Field(
        default=None,
        description=(
            "Output height in pixels. Omit for server default 512. Must be a "
            "positive multiple of 64 and no greater than the configured cap "
            "(default 768)."
        ),
    )
    num_frames: int | None = Field(
        default=None,
        description=(
            "Number of output frames. Omit for server default 97. Must satisfy "
            "`1 + 8*k` (for example 97, 161, 241, 481, 721) and stay within the "
            "configured cap (default 721). Duration is `num_frames / fps`."
        ),
    )
    fps: int | None = Field(
        default=None,
        description=(
            "Output frame rate. Omit for server default 24. Must be positive; it "
            "sets playback duration but does not materially reduce generation work."
        ),
    )
    seed: int | None = Field(
        default=None,
        description=(
            "Random seed for reproducibility. Omit for a random seed (the resolved "
            "seed is recorded in the result `params`)."
        ),
    )
    image_strength: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "First-frame conditioning strength in 0..1. 1.0 adheres tightly to "
            "the input frame; lower values such as ~0.7 allow larger motion or "
            "composition changes."
        ),
    )
    end_image_strength: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Last-frame conditioning strength in 0..1. Omit to let mlx-video use "
            "its default behavior for the selected mode."
        ),
    )
    generate_audio: bool = Field(
        default=False,
        description=(
            "Ask LTX-2 to synthesize synchronized audio for the MP4. Mutually "
            "exclusive with an `audio` FileRef."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "prompt": self.prompt,
            "image": self.image.model_dump(mode="json")
            if self.image is not None
            else None,
            "end_image": self.end_image.model_dump(mode="json")
            if self.end_image is not None
            else None,
            "audio": self.audio.model_dump(mode="json")
            if self.audio is not None
            else None,
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "fps": self.fps,
            "seed": self.seed,
            "image_strength": self.image_strength,
            "end_image_strength": self.end_image_strength,
            "generate_audio": self.generate_audio,
        }
