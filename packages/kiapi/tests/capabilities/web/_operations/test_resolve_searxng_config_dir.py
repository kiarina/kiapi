from pathlib import Path

from kiapi.capabilities.web._operations.resolve_searxng_config_dir import (
    resolve_searxng_config_dir,
)
from kiapi.core.app._settings import settings_manager as app_settings_manager


def test_resolve_searxng_config_dir_copies_bundled_settings(
    tmp_path: Path,
) -> None:
    app_settings_manager.user_config = {"user_config_dir": str(tmp_path / "config")}
    try:
        config_dir = resolve_searxng_config_dir()
    finally:
        app_settings_manager.reset_user_config()

    settings_path = config_dir / "settings.yml"
    assert config_dir == tmp_path / "config" / "searxng"
    assert settings_path.exists()
    assert "use_default_settings:" in settings_path.read_text()


def test_resolve_searxng_config_dir_keeps_existing_settings(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config" / "searxng"
    config_dir.mkdir(parents=True)
    settings_path = config_dir / "settings.yml"
    settings_path.write_text("custom: true\n")

    app_settings_manager.user_config = {"user_config_dir": str(tmp_path / "config")}
    try:
        resolved = resolve_searxng_config_dir()
    finally:
        app_settings_manager.reset_user_config()

    assert resolved == config_dir
    assert settings_path.read_text() == "custom: true\n"
