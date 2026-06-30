import os

from platformdirs import PlatformDirs

from .._settings import settings_manager

_APP_NAME = "kiapi-proxy"
_APP_AUTHOR = "kiarina"


def get_user_cache_dir() -> str:
    settings = settings_manager.get_settings()

    if settings.user_cache_dir:
        return os.path.expanduser(settings.user_cache_dir)

    if xdg_cache_home := os.getenv("XDG_CACHE_HOME"):
        return os.path.join(xdg_cache_home, _APP_NAME)

    platform_dirs = PlatformDirs(
        appname=_APP_NAME,
        appauthor=_APP_AUTHOR,
    )

    return platform_dirs.user_cache_dir


def get_user_config_dir() -> str:
    settings = settings_manager.get_settings()

    if settings.user_config_dir:
        return os.path.expanduser(settings.user_config_dir)

    if xdg_config_home := os.getenv("XDG_CONFIG_HOME"):
        return os.path.join(xdg_config_home, _APP_NAME)

    platform_dirs = PlatformDirs(
        appname=_APP_NAME,
        appauthor=_APP_AUTHOR,
    )

    return platform_dirs.user_config_dir


def get_user_data_dir() -> str:
    settings = settings_manager.get_settings()

    if settings.user_data_dir:
        return os.path.expanduser(settings.user_data_dir)

    if xdg_data_home := os.getenv("XDG_DATA_HOME"):
        return os.path.join(xdg_data_home, _APP_NAME)

    platform_dirs = PlatformDirs(
        appname=_APP_NAME,
        appauthor=_APP_AUTHOR,
    )

    return platform_dirs.user_data_dir
