"""``/v1/image/ideogram4/generate`` result payload (the Job ``result`` shape).

Mirrors the dict returned by ``capabilities/ideogram4/_models/ideogram4._store_image``
so the produced image result is self-describing in OpenAPI. It is an output-side
projection of the model result (not a model-coupled view), so it lives under
``api/image/ideogram4/_views``.

``ImageResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock generation time in seconds (model run only)."
    )


class ImageResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded ideogram4 generate job."""

    model: str = Field(description="Resolved model variant that produced the image.")
    prompt: str | dict[str, Any] = Field(
        description="The prompt used for the run (plain text or JSON caption)."
    )

    file_id: str = Field(
        description=(
            "Files-API id of the produced image. Fetch metadata at "
            "GET /v1/files/{id} or bytes at /download. This is also the artifact "
            "returned as raw bytes by a single-artifact sync call."
        )
    )
    image_bytes: int = Field(description="Size of the produced image in bytes.")

    width: int = Field(description="Width in pixels of the produced image.")
    height: int = Field(description="Height in pixels of the produced image.")

    params: dict[str, Any] = Field(
        description=(
            "Resolved parameters actually used for the run (model, prompt, preset, "
            "seed, width, height, quantize, format, quality, …), so the result is "
            "reproducible."
        )
    )
    safety_filter_note: str = Field(
        description=(
            "Reminder that Ideogram 4 may return an 'Image blocked by safety filter' "
            "image, which kiapi stores as the artifact rather than raising an error."
        )
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
