from typing import Any

from pydantic import BaseModel, Field

from .._types.file_id import FileID


class FileRecord(BaseModel):
    """A stored file's metadata. Doubles as the Files API response schema.

    ``path`` is the on-disk location and is internal to the file store; it is
    excluded from serialization so ``model_dump()`` yields the API/sidecar shape.
    """

    file_id: FileID = Field(
        ...,
        description="Persistent file id. Use this in FileRef inputs or download it with GET /v1/files/{file_id}/download.",
        examples=["file_0123456789abcdef"],
    )
    filename: str = Field(
        ...,
        description="Original or generated filename associated with the stored bytes.",
        examples=["image_1766200000.png"],
    )
    content_type: str = Field(
        ...,
        description="Media type of the stored file.",
        examples=["image/png"],
    )
    size: int = Field(
        ...,
        ge=0,
        description="File size in bytes.",
        examples=[123456],
    )
    created_at: float = Field(
        ...,
        description="Unix timestamp when the file was stored.",
        examples=[1766200000.0],
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Capability-specific metadata such as seed, request params, timings, dimensions, or artifact kind.",
        examples=[{"model": "turbo", "width": 1024, "height": 1024}],
    )
    path: str = Field(..., exclude=True)
