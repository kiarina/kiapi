from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PythonPackageResource(BaseModel):
    """A Python package installed into the current kiapi environment."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["python_package"] = Field(
        default="python_package",
        description="Resource kind discriminator.",
        examples=["python_package"],
    )
    package: str = Field(
        ...,
        description="Distribution name used when uninstalling the package.",
        examples=["mlx-video"],
    )
    spec: str = Field(
        ...,
        description="Package spec used when installing the package.",
        examples=["mlx-video @ git+https://github.com/Blaizzy/mlx-video.git@<commit>"],
    )
    import_name: str = Field(
        ...,
        description="Module imported to verify that the package is ready.",
        examples=["mlx_video.models.ltx_2.generate"],
    )
    verify_attrs: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Attributes that must exist on the imported module.",
        examples=[["PipelineType", "generate_video"]],
    )
    label_name: str | None = Field(
        default=None,
        description="Optional friendly label; defaults to the package name.",
        examples=["mlx-video-ltx2"],
    )
    disk_gb: float | None = Field(
        default=None,
        ge=0.0,
        description="Approximate on-disk size of the installed package in GB.",
        examples=[0.5],
    )

    @computed_field(  # type: ignore[prop-decorator]
        description="Label accepted by kiapi activate/deactivate --repo.",
    )
    @property
    def label(self) -> str:
        return self.label_name or self.package

    @property
    def key(self) -> str:
        attrs = ",".join(self.verify_attrs)
        return f"{self.kind}:{self.package}:{self.spec}:{self.import_name}:{attrs}"
