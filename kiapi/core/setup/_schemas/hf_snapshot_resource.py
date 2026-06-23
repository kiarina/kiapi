from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class HfSnapshotResource(BaseModel):
    """A Hugging Face snapshot that must be downloaded before the model runs."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["hf_snapshot"] = Field(
        default="hf_snapshot",
        description="Resource kind discriminator.",
        examples=["hf_snapshot"],
    )
    repo: str = Field(
        ...,
        description="Hugging Face repository id to snapshot-download.",
        examples=["mlx-community/Qwen3-Omni-30B-A3B-Instruct-4bit"],
    )
    disk_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Approximate on-disk size of the snapshot in GB.",
        examples=[21.8],
    )
    revision: str | None = Field(
        default=None,
        description="Git revision (branch, tag, or commit) to pin; None means main.",
        examples=["main"],
    )
    local_dir: str | None = Field(
        default=None,
        description="If set, materialize into this directory instead of the HF cache.",
        examples=[None],
    )

    @computed_field(  # type: ignore[prop-decorator]
        description="Label accepted by kiapi activate/deactivate --repo.",
    )
    @property
    def label(self) -> str:
        return self.repo

    @property
    def key(self) -> str:
        revision = self.revision or "main"
        local_dir = str(Path(self.local_dir).expanduser()) if self.local_dir else ""
        return f"{self.kind}:{self.repo}:{revision}:{local_dir}"
