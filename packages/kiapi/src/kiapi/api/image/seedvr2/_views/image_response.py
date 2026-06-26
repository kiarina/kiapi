"""``/v1/image/seedvr2/upscale`` result payload (the Job ``result`` shape).

Mirrors the dict returned by ``capabilities/seedvr2/_models/seedvr2._store_image``
so the upscaled image result is self-describing in OpenAPI. It is an output-side
projection of the model result (not a model-coupled view), so it lives under
``api/image/seedvr2/_views``.

``ImageResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock upscale time in seconds (model run only)."
    )


class ImageResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded seedvr2 upscale job."""

    model: str = Field(
        description="Resolved model variant that produced the image (3b or 7b)."
    )

    file_id: str = Field(
        description=(
            "Files-API id of the upscaled image. Fetch metadata at "
            "GET /v1/files/{id} or bytes at /download. This is also the artifact "
            "returned as raw bytes by a single-artifact sync call."
        )
    )
    image_bytes: int = Field(description="Size of the produced image in bytes.")

    input_width: int = Field(description="Width in pixels of the input image.")
    input_height: int = Field(description="Height in pixels of the input image.")
    width: int = Field(description="Width in pixels of the upscaled image.")
    height: int = Field(description="Height in pixels of the upscaled image.")

    params: dict[str, Any] = Field(
        description=(
            "Resolved parameters actually used for the run (model, resolution, "
            "softness, seed, quantize, format, quality), so the result is "
            "reproducible."
        )
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
