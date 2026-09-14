"""Depth Pro request model.

Image → depth map (Depth Pro). One endpoint serves both sync and async via
``mode``. The input image is referenced by ``image`` (FileRef). A ``quantize``
override runs a one-off transient model; otherwise the resident model is used.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kiapi.core.file import FileRef


class EstimateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = Field(
        default=None,
        description=(
            "Model variant (see GET /v1/image/depthpro/models). Omit for the "
            "default `base`. Aliases `depthpro`, `depth-pro`, `DepthPro` are accepted."
        ),
    )
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description=(
            "`sync` waits for the depth map (504 on timeout); `async` returns 202 "
            "with a job_id immediately — poll GET /v1/jobs/{job_id}."
        ),
    )

    image: FileRef = Field(
        description=(
            "Input image to estimate depth for, as a Files-API file id, http(s) "
            "URL, or data URL. Must not exceed the configured input pixel cap."
        ),
    )
    quantize: int | None = Field(
        default=None,
        description=(
            "Quantization bits, one of {3, 4, 5, 6, 8}. Omit to use the server "
            "default (8). A value differing from the resident model's quantization "
            "runs a one-off transient model (no resident reuse), so it is slower."
        ),
    )

    include_depth_data: bool = Field(
        default=True,
        description=(
            "When true, also store a compressed NPZ with the raw float depth array "
            "and min/max depth (`depth_data_file_id`) alongside the grayscale PNG. "
            "When false, only the PNG is produced, so a sync call can return the raw "
            "PNG bytes directly (single artifact, unless Accept: application/json)."
        ),
    )

    def gen_params(self) -> dict:
        return {
            "image": self.image.model_dump(mode="json"),
            "quantize": self.quantize,
            "include_depth_data": self.include_depth_data,
        }
