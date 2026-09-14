from pathlib import Path

from kiarina.utils.app import settings_manager as app_settings_manager

from kiapi.capabilities.acestep import register
from kiapi.core.model import model_registry
from kiapi.core.setup import HfSnapshotResource, PythonVenvResource


def test_register_adds_acestep_venv_setup_resource() -> None:
    register()

    specs = model_registry.list_specs("acestep")

    assert specs
    for spec in specs:
        assert any(
            isinstance(resource, PythonVenvResource)
            and resource.label == "acestep-venv"
            for resource in spec.setup_resources
        )


def test_register_uses_user_data_dir_for_default_setup_paths(tmp_path: Path) -> None:
    app_settings_manager.user_config = {"user_data_dir": str(tmp_path / "data")}
    existing_count = len(model_registry.list_specs())
    try:
        register()
    finally:
        app_settings_manager.reset_user_config()

    specs = model_registry.list_specs()[existing_count:]
    root = tmp_path / "data" / "acestep"

    assert specs
    for spec in specs:
        assert any(
            isinstance(resource, PythonVenvResource)
            and resource.path == str(root / ".venv")
            for resource in spec.setup_resources
        )
        assert any(
            isinstance(resource, HfSnapshotResource)
            and resource.repo == "ACE-Step/Ace-Step1.5"
            and resource.local_dir == str(root / "checkpoints")
            for resource in spec.setup_resources
        )
