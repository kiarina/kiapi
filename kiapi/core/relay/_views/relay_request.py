from pydantic import BaseModel, Field, field_validator

from .._types.relay_method import RelayMethod


class RelayRequest(BaseModel):
    method: RelayMethod
    path: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, object] | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("path must be an absolute local API path")
        if "://" in value:
            raise ValueError("path must not contain an URL scheme")
        return value
