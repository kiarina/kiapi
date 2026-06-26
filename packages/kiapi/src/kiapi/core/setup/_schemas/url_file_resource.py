from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class UrlFileResource(BaseModel):
    """A single file fetched from a URL and cached at a local path."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["url_file"] = Field(
        default="url_file",
        description="Resource kind discriminator.",
        examples=["url_file"],
    )
    url: str = Field(
        ...,
        description="Source URL the file is downloaded from.",
        examples=["https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt"],
    )
    path: str = Field(
        ...,
        description="Local path the downloaded file is stored at.",
        examples=["./checkpoints/depth-pro/depth_pro.pt"],
    )
    disk_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Approximate on-disk size of the file in GB.",
        examples=[1.9],
    )

    @computed_field(  # type: ignore[prop-decorator]
        description="Label accepted by kiapi activate/deactivate --repo.",
    )
    @property
    def label(self) -> str:
        return self.url

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.url}:{Path(self.path).expanduser()}"
