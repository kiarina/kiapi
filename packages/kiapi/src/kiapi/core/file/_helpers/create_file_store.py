from .._services.file_store import FileStore
from .._settings import settings_manager


def create_file_store() -> FileStore:
    settings = settings_manager.get_settings()
    return FileStore(settings)
