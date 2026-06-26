from pathlib import Path

from kiapi.core.app import get_user_config_dir


def get_user_settings_path() -> Path:
    return Path(get_user_config_dir()).expanduser() / "settings.yaml"
