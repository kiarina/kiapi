"""``/v1/audio/acestep/{generate,cover,repaint}`` result payload (the Job ``result``).

Mirrors the dict returned by ``capabilities/acestep/_models/acestep.generate_track``
so the produced track is self-describing in OpenAPI. It is an output-side projection
of the model result (not a model-coupled view), so it lives under
``api/audio/acestep/_views``. The same single-track shape is returned by generate,
cover, and repaint; ``src`` is present only for cover/repaint.

``TrackResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock generation time in seconds (subprocess run only)."
    )


class TrackResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded generate/cover/repaint job."""

    task: str = Field(
        description="Operation that produced the track: text2music, cover, or repaint."
    )
    model: str = Field(
        description="Resolved preset that produced the track (xl-base or turbo)."
    )

    file_id: str = Field(
        description=(
            "Files-API id of the produced WAV. Fetch metadata at GET /v1/files/{id} "
            "or bytes at /download. This is also the artifact returned as raw bytes "
            "by a single-artifact sync call."
        )
    )
    audio_bytes: int = Field(description="Size of the produced WAV in bytes.")

    src: str | None = Field(
        default=None,
        description=(
            "Files-API id of the source track. Present for cover/repaint; null for "
            "generate (which takes no source)."
        ),
    )

    params: dict[str, Any] = Field(
        description=(
            "Resolved parameters actually used for the run (prompt, lyrics, duration, "
            "seed, inference_steps, guidance_scale, shift, …), so the result is "
            "reproducible."
        )
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
