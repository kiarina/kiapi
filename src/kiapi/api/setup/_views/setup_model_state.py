from typing import Literal

from pydantic import BaseModel, Field

from .setup_resource_state import SetupResourceState


class SetupModelState(BaseModel):
    domain: str = Field(..., description="Modality bucket.", examples=["image"])
    family: str = Field(..., description="Family identifier.", examples=["zimage"])
    name: str = Field(..., description="Model variant name.", examples=["base"])
    default: bool = Field(
        ...,
        description="Whether this is the family's default variant.",
        examples=[False],
    )
    status: Literal["ready", "missing", "none"] = Field(
        ...,
        description="ready when every resource is present, missing when any is "
        "absent, none when the model needs no setup.",
        examples=["missing"],
    )
    size_gb: float = Field(
        ...,
        description="Approximate total on-disk size of the model's resources in GB.",
        examples=[19.0],
    )
    resources: list[SetupResourceState] = Field(
        default_factory=list,
        description="Setup resources the model needs.",
    )
