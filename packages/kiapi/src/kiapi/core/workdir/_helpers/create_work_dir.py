import tempfile
from pathlib import Path

from .._settings import settings_manager


def create_work_dir(purpose: str) -> Path:
    root = Path(settings_manager.get_settings().tmp_root).expanduser()
    parent = root / purpose
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(dir=parent))
