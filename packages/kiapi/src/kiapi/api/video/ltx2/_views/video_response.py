"""``/v1/video/ltx2/generate`` result payload (the Job ``result`` shape).

Mirrors the dict returned by ``capabilities/ltx2/_models/ltx2.run_generate`` so
the MP4 result is self-describing in OpenAPI. It is an output-side projection of
the model result, so it lives under ``api/video/ltx2/_views``.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock generation time in seconds (model run only)."
    )


class VideoResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded LTX-2 generation job."""

    file_id: str = Field(
        description=(
            "Files-API id of the produced MP4. Fetch metadata at GET /v1/files/{id} "
            "or bytes at /download. This is also the artifact returned as raw "
            "bytes by a single-artifact sync call."
        )
    )
    video_bytes: int = Field(description="Size of the produced MP4 in bytes.")

    mode: Literal[
        "T2V",
        "I2V",
        "I2V(first+last)",
        "I2V(last)",
        "A2V",
        "A2V+I2V",
        "T2V+Audio",
    ] = Field(
        description=(
            "Detected generation mode, inferred from image/end_image/audio inputs "
            "and `generate_audio`."
        )
    )
    prompt: str = Field(description="Prompt used for the generation.")
    params: dict[str, Any] = Field(
        description=(
            "Resolved parameters actually used for the run (prompt, dimensions, "
            "frame count, fps, seed, conditioning strengths, and generate_audio), "
            "so the result is reproducible."
        )
    )
    has_audio: bool = Field(
        description=(
            "Whether an auxiliary audio track was produced or supplied and muxed "
            "into the MP4."
        )
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
