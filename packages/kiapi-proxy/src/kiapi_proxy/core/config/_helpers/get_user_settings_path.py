from pathlib import Path

from kiarina.utils.app import user_directory


def get_user_settings_path() -> Path:
    return user_directory.get_user_config_dir() / "settings.yaml"
