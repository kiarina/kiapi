from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class LocalPathResource(BaseModel):
    """A local filesystem path that must already exist before the model runs."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["local_path"] = Field(
        default="local_path",
        description="Resource kind discriminator.",
        examples=["local_path"],
    )
    path: str = Field(
        ...,
        description="Filesystem path that must exist for the model to run.",
        examples=["./checkpoints/ace-step-v1.5-xl-base"],
    )
    label_name: str | None = Field(
        default=None,
        description="Optional friendly label; defaults to the path when unset.",
        examples=["ace-step-xl-base"],
    )
    disk_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Approximate on-disk size of the path in GB.",
        examples=[12.0],
    )

    @computed_field(  # type: ignore[prop-decorator]
        description="Label accepted by kiapi activate/deactivate --repo.",
    )
    @property
    def label(self) -> str:
        return self.label_name or self.path

    @property
    def key(self) -> str:
        return f"{self.kind}:{Path(self.path).expanduser()}"
