from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.get_log_level import get_log_level
    from ._helpers.setup_logger import setup_logger
    from ._settings import settings_manager
    from ._types.log_level import LogLevel

__all__ = [
    "LogLevel",
    "get_log_level",
    "settings_manager",
    "setup_logger",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "LogLevel": "._types.log_level",
        "get_log_level": "._helpers.get_log_level",
        "settings_manager": "._settings",
        "setup_logger": "._helpers.setup_logger",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
