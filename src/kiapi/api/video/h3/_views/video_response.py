"""``/v1/video/h3/generate`` result payload (the Job ``result`` shape)."""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock time in seconds, from starting mlx-serve to the MP4."
    )


class VideoResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded MiniMax H3 generation job."""

    file_id: str = Field(
        description=(
            "Files-API id of the produced MP4. Fetch metadata at GET /v1/files/{id} "
            "or bytes at /download."
        )
    )
    video_bytes: int = Field(description="Size of the produced MP4 in bytes.")
    prompt: str = Field(description="Prompt used for the generation.")
    params: dict[str, Any] = Field(
        description=(
            "Resolved parameters actually used for the run (dimensions, frame count, "
            "steps, turbo, fast, use_video_audio, seed), so the result is reproducible. "
            "`enhanced_prompt` is the rewritten prompt sent to the model, or null when "
            "the request prompt was used as is."
        )
    )
    references: dict[str, int] = Field(
        description="Number of references passed, by kind (images, videos, audios)."
    )
    has_audio: bool = Field(description="Whether the MP4 carries the generated audio.")
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
