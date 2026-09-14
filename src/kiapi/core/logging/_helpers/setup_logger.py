import logging

from .._settings import settings_manager

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logger() -> None:
    settings = settings_manager.get_settings()
    log_level = logging.getLevelNamesMapping()[settings.log_level]

    logging.basicConfig(level=log_level, format=_LOG_FORMAT)
    logging.getLogger().setLevel(log_level)
    logging.getLogger("kiapi").setLevel(log_level)
