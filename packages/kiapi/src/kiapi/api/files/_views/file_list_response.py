from pydantic import BaseModel, Field

from kiapi.core.file import FileRecord


class FileListResponse(BaseModel):
    object: str = Field(
        default="list",
        description="OpenAI-style list envelope marker.",
        examples=["list"],
    )
    data: list[FileRecord] = Field(
        default_factory=list,
        description="Stored files, including uploaded inputs and generated artifacts.",
    )
