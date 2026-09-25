from pydantic import BaseModel, Field


class SetupResourceState(BaseModel):
    kind: str = Field(
        ...,
        description="Resource kind, such as hf_snapshot, docker_image, or python_venv.",
        examples=["hf_snapshot"],
    )
    label: str = Field(
        ...,
        description="Label accepted by kiapi activate/deactivate --repo.",
        examples=["Tongyi-MAI/Z-Image"],
    )
    ready: bool = Field(
        ...,
        description="Whether the resource is present on this machine.",
        examples=[False],
    )
    disk_gb: float | None = Field(
        default=None,
        description="Approximate on-disk size in GB, when known.",
        examples=[19.0],
    )
    detail: str = Field(
        default="",
        description="Where the resource was found, or why it is missing.",
        examples=["/cache/models--Tongyi-MAI--Z-Image"],
    )
    activate_command: str = Field(
        ...,
        description="CLI command that sets up this resource.",
        examples=["kiapi activate --repo Tongyi-MAI/Z-Image"],
    )
