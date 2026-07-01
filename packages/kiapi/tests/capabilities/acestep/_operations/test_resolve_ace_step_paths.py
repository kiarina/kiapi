from pathlib import Path

from kiapi.capabilities.acestep._operations.resolve_ace_step_paths import (
    resolve_ace_step_paths,
)
from kiapi.capabilities.acestep._settings import AceStepSettings
from kiapi.core.app import settings_manager as app_settings_manager


def test_ace_step_path_settings_default_to_none() -> None:
    settings = AceStepSettings()

    assert settings.python_path is None
    assert settings.project_root is None
    assert settings.checkpoint_dir is None


def test_resolve_ace_step_paths_defaults_to_user_data_acestep_dir(
    tmp_path: Path,
) -> None:
    app_settings_manager.user_config = {"user_data_dir": str(tmp_path / "data")}
    try:
        paths = resolve_ace_step_paths(AceStepSettings())
    finally:
        app_settings_manager.reset_user_config()

    root = tmp_path / "data" / "acestep"
    assert paths.python_path == str(root / ".venv" / "bin" / "python")
    assert paths.venv_path == str(root / ".venv")
    assert paths.project_root == str(root / "project")
    assert paths.checkpoint_dir == str(root / "checkpoints")


def test_resolve_ace_step_paths_uses_explicit_settings() -> None:
    paths = resolve_ace_step_paths(
        AceStepSettings(
            python_path="~/custom-acestep/bin/python",
            project_root="~/custom-acestep/project",
            checkpoint_dir="~/custom-acestep/checkpoints",
        )
    )

    home = Path.home()
    assert paths.python_path == str(home / "custom-acestep" / "bin" / "python")
    assert paths.venv_path == str(home / "custom-acestep")
    assert paths.project_root == str(home / "custom-acestep" / "project")
    assert paths.checkpoint_dir == str(home / "custom-acestep" / "checkpoints")
