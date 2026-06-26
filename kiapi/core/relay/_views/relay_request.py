from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from .._schemas.relay_multipart_body import RelayMultipartBody
from .._types.relay_method import RelayMethod


class RelayRequest(BaseModel):
    method: RelayMethod
    path: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, object] | None = None
    multipart: RelayMultipartBody | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("path must be an absolute local API path")
        if "://" in value:
            raise ValueError("path must not contain an URL scheme")
        return value

    @model_validator(mode="after")
    def validate_body_kind(self) -> Self:
        if self.body is not None and self.multipart is not None:
            raise ValueError("body and multipart cannot both be set")
        return self
