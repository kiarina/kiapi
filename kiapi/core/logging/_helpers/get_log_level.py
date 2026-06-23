import logging

from .._settings import settings_manager


def get_log_level() -> int:
    settings = settings_manager.get_settings()
    return logging.getLevelNamesMapping()[settings.log_level]
