from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class DockerImageResource(BaseModel):
    """A Docker image that must be pulled before the model (backend) runs."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["docker_image"] = Field(
        default="docker_image",
        description="Resource kind discriminator.",
        examples=["docker_image"],
    )
    image: str = Field(
        ...,
        description="Docker image reference to pull.",
        examples=["searxng/searxng:latest"],
    )
    disk_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Approximate on-disk size of the image in GB.",
        examples=[0.4],
    )

    @computed_field(  # type: ignore[prop-decorator]
        description="Label accepted by kiapi activate/deactivate --repo.",
    )
    @property
    def label(self) -> str:
        return self.image

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.image}"
