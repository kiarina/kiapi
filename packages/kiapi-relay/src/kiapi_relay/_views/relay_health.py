from pydantic import BaseModel, Field

from .._types.relay_name import RelayName


class RelayHealth(BaseModel):
    name: RelayName = Field(
        ...,
        description="Name of the relay started with the API server.",
        examples=["gcp"],
    )
    running: bool = Field(
        ...,
        description="Whether the relay watch loop is currently running.",
        examples=[True],
    )
    failed: bool = Field(
        ...,
        description="Whether the relay watch loop stopped after raising an error.",
        examples=[False],
    )
