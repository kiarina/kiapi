from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AceStepPaths(BaseModel):
    """Resolved local paths used by the ACE-Step subprocess and setup resources."""

    model_config = ConfigDict(frozen=True)

    python_path: str
    venv_path: str
    project_root: str
    checkpoint_dir: str

    @classmethod
    def from_paths(
        cls,
        *,
        python_path: Path,
        project_root: Path,
        checkpoint_dir: Path,
    ) -> "AceStepPaths":
        return cls(
            python_path=str(python_path),
            venv_path=str(python_path.parent.parent),
            project_root=str(project_root),
            checkpoint_dir=str(checkpoint_dir),
        )
