from pathlib import Path

from kiapi.core.app import get_user_data_dir

from .._schemas.ace_step_paths import AceStepPaths
from .._settings import AceStepSettings


def resolve_ace_step_paths(settings: AceStepSettings) -> AceStepPaths:
    root = Path(get_user_data_dir()).expanduser() / "acestep"
    python_path = (
        Path(settings.python_path).expanduser()
        if settings.python_path is not None
        else root / ".venv" / "bin" / "python"
    )
    project_root = (
        Path(settings.project_root).expanduser()
        if settings.project_root is not None
        else root / "project"
    )
    checkpoint_dir = (
        Path(settings.checkpoint_dir).expanduser()
        if settings.checkpoint_dir is not None
        else root / "checkpoints"
    )
    return AceStepPaths.from_paths(
        python_path=python_path,
        project_root=project_root,
        checkpoint_dir=checkpoint_dir,
    )
