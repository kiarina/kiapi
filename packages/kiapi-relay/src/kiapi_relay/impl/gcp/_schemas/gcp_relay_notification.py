from pydantic import BaseModel, field_validator


class GCPRelayNotification(BaseModel):
    session_id: str
    source_node_id: str

    @field_validator("session_id", "source_node_id")
    @classmethod
    def validate_path_segment(cls, value: str) -> str:
        if not value or "/" in value or value in {".", ".."}:
            raise ValueError("RTDB path identifiers must be non-empty path segments")
        return value
