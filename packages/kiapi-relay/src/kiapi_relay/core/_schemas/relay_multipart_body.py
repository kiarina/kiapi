from pydantic import BaseModel, Field

from .relay_multipart_file import RelayMultipartFile


class RelayMultipartBody(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)
    files: list[RelayMultipartFile]
