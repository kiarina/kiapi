from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PythonVenvResource(BaseModel):
    """A Python virtual environment that must be built before the model runs."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["python_venv"] = Field(
        default="python_venv",
        description="Resource kind discriminator.",
        examples=["python_venv"],
    )
    path: str = Field(
        ...,
        description="Virtual environment directory.",
        examples=[".venv-acestep"],
    )
    python: str = Field(
        default="3.12",
        description="Python version or executable used to create the virtual environment.",
        examples=["3.12"],
    )
    packages: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="Pip package specs installed into the virtual environment.",
        examples=[["ace-step @ git+https://github.com/ace-step/ACE-Step-1.5.git"]],
    )
    import_name: str = Field(
        ...,
        description="Module imported to verify that the environment is ready.",
        examples=["acestep"],
    )
    label_name: str | None = Field(
        default=None,
        description="Optional friendly label; defaults to the venv path when unset.",
        examples=["acestep-venv"],
    )
    disk_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Approximate on-disk size of the virtual environment in GB.",
        examples=[8.0],
    )

    @computed_field(  # type: ignore[prop-decorator]
        description="Label accepted by kiapi activate/deactivate --repo.",
    )
    @property
    def label(self) -> str:
        return self.label_name or self.path

    @property
    def key(self) -> str:
        packages = ",".join(self.packages)
        return (
            f"{self.kind}:{Path(self.path).expanduser()}:{self.python}:"
            f"{packages}:{self.import_name}"
        )
