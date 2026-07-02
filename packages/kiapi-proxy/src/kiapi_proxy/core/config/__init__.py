from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.user_config_error import UserConfigError
    from ._helpers.get_user_settings_path import get_user_settings_path
    from ._helpers.load_user_settings import load_user_settings

__all__ = [
    "UserConfigError",
    "get_user_settings_path",
    "load_user_settings",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "UserConfigError": "._exceptions.user_config_error",
        "get_user_settings_path": "._helpers.get_user_settings_path",
        "load_user_settings": "._helpers.load_user_settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
