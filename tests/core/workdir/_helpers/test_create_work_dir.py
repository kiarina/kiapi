from pathlib import Path

from kiapi.core.workdir import create_work_dir, settings_manager


def test_create_work_dir_creates_purpose_directory(tmp_path: Path) -> None:
    settings_manager.user_config = {"tmp_root": str(tmp_path)}
    try:
        workdir = create_work_dir("image/zimage")
    finally:
        settings_manager.reset_user_config()

    assert workdir.exists()
    assert workdir.is_dir()
    assert workdir.parent == tmp_path / "image" / "zimage"
