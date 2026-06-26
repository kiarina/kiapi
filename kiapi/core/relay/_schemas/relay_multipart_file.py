import base64
import binascii

from pydantic import BaseModel, Field


class RelayMultipartFile(BaseModel):
    field: str = "file"
    filename: str
    content_type: str | None = None
    content_base64: str = Field(
        description="Base64-encoded file bytes for a multipart/form-data part.",
    )

    def content(self) -> bytes:
        try:
            return base64.b64decode(self.content_base64, validate=True)
        except binascii.Error as exc:
            raise ValueError("content_base64 must be valid base64") from exc
