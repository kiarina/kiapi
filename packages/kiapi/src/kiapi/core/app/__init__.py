from kiarina.utils.app import (
    AppAlreadyConfiguredError,
    AppSettings,
    settings_manager,
)
from kiarina.utils.app import configure as _configure
from kiarina.utils.app import user_directory as _user_directory

from ._schemas.app_context import AppContext

get_user_cache_dir = _user_directory.get_user_cache_dir
get_user_config_dir = _user_directory.get_user_config_dir
get_user_data_dir = _user_directory.get_user_data_dir


def configure_app() -> None:
    """Set the application identity used to resolve user directories.

    Idempotent so it can be called from every entry point (the CLI and the
    ASGI app) without ordering assumptions.
    """
    try:
        _configure("kiapi", "kiarina")
    except AppAlreadyConfiguredError:
        pass


__all__ = [
    "AppContext",
    "AppSettings",
    "configure_app",
    "get_user_cache_dir",
    "get_user_config_dir",
    "get_user_data_dir",
    "settings_manager",
]
