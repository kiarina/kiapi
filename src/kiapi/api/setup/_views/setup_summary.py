from pydantic import BaseModel, Field


class SetupSummary(BaseModel):
    models_total: int = Field(
        ..., ge=0, description="Registered models.", examples=[26]
    )
    models_ready: int = Field(
        ..., ge=0, description="Models whose resources are all present.", examples=[23]
    )
    resources_total: int = Field(
        ..., ge=0, description="Distinct setup resources.", examples=[29]
    )
    resources_ready: int = Field(
        ..., ge=0, description="Distinct setup resources present.", examples=[26]
    )
    installed_gb: float = Field(
        ...,
        ge=0.0,
        description="Approximate size of present resources in GB.",
        examples=[686.51],
    )
    total_gb: float = Field(
        ...,
        ge=0.0,
        description="Approximate size of all resources in GB.",
        examples=[790.01],
    )
