from pydantic import BaseModel, Field


class FileDeleteResponse(BaseModel):
    deleted: bool = Field(
        ...,
        description="True when the file record and stored bytes were deleted.",
        examples=[True],
    )
    file_id: str = Field(
        ...,
        description="Deleted file id.",
        examples=["file_0123456789abcdef"],
    )
