import shutil
from importlib.resources import files
from pathlib import Path

from kiarina.utils.app import user_directory


def resolve_searxng_config_dir() -> Path:
    config_dir = user_directory.get_user_config_dir() / "searxng"
    config_dir.mkdir(parents=True, exist_ok=True)

    settings_path = config_dir / "settings.yml"
    if not settings_path.exists():
        bundled_settings = (
            files("kiapi.capabilities.web.resources.searxng") / "settings.yml"
        )
        with bundled_settings.open("rb") as source:
            with settings_path.open("wb") as target:
                shutil.copyfileobj(source, target)

    return config_dir
