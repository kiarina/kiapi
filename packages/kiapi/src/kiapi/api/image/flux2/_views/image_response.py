"""``/v1/image/flux2/{generate,edit}`` result payload (the Job ``result`` shape).

Mirrors the dict returned by ``capabilities/flux2/_models/flux2._store_image`` so
the produced image result is self-describing in OpenAPI. It is an output-side
projection of the model result (not a model-coupled view), so it lives under
``api/image/flux2/_views``. ``generate`` and ``edit`` produce the same shape, so
both endpoints share this one view.

``ImageResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock generation time in seconds (model run only)."
    )


class ImageResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded flux2 generate/edit job."""

    model: str = Field(
        description=(
            "Resolved model variant that produced the image "
            "(klein-9b | klein-base-4b | klein-base-9b)."
        )
    )
    prompt: str = Field(description="The prompt used for the run.")

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
            "Resolved parameters actually used for the run (model, seed, steps, "
            "guidance, quantize, scheduler, format, quality, loras, …), so the "
            "result is reproducible."
        )
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
