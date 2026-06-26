from pydantic import BaseModel, Field

from .._schemas.relay_file_body import RelayFileBody
from .._schemas.relay_json_body import RelayJsonBody


class RelayResponse(BaseModel):
    status: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: RelayJsonBody | RelayFileBody | None = Field(
        default=None,
        discriminator="type",
    )
