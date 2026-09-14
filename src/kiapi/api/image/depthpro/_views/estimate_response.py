"""``/v1/image/depthpro/estimate`` result payload (the Job ``result`` shape).

Mirrors the dict returned by ``capabilities/depthpro/_models/depthpro._estimate``
so the depth-map result is self-describing in OpenAPI. It is an output-side
projection of the model result (not a model-coupled view), so it lives under
``api/image/depthpro/_views``.

``EstimateResponse`` is the sole public element; nested pieces stay private.
"""

from typing import Any

from pydantic import BaseModel, Field


class _Timings(BaseModel):
    total_s: float = Field(
        description="Wall-clock depth-estimation time in seconds (model run only)."
    )


class EstimateResponse(BaseModel):
    """Capability-specific ``result`` for a succeeded depthpro estimate job."""

    model: str = Field(
        description="Resolved model variant that produced the depth map."
    )

    depth_image_file_id: str = Field(
        description=(
            "Files-API id of the grayscale depth PNG (near = bright, far = dark). "
            "Fetch metadata at GET /v1/files/{id} or bytes at /download. This is "
            "also the artifact returned as raw bytes by a single-artifact sync call."
        )
    )
    depth_image_bytes: int = Field(description="Size of the depth PNG in bytes.")
    depth_data_file_id: str | None = Field(
        description=(
            "Files-API id of the compressed NPZ holding the raw float depth array "
            "plus min/max depth, or null when `include_depth_data` was false."
        )
    )
    depth_data_bytes: int | None = Field(
        description="Size of the NPZ in bytes, or null when no depth data was stored."
    )

    input_width: int = Field(description="Width in pixels of the submitted image.")
    input_height: int = Field(description="Height in pixels of the submitted image.")
    input_mode: str = Field(
        description="PIL mode of the submitted image (e.g. RGB, L, RGBA)."
    )

    width: int = Field(description="Width in pixels of the produced depth map.")
    height: int = Field(description="Height in pixels of the produced depth map.")
    mode: str = Field(description="PIL mode of the produced depth PNG (typically L).")

    array_shape: list[int] = Field(
        description="Shape of the raw depth array stored in the NPZ (rows, cols)."
    )
    min_depth: float = Field(
        description="Minimum depth value in the raw array, in meters."
    )
    max_depth: float = Field(
        description="Maximum depth value in the raw array, in meters."
    )

    params: dict[str, Any] = Field(
        description="Resolved parameters used for the run (model, quantize, etc.)."
    )
    timings: _Timings = Field(description="kiapi extension: server-side timing.")
