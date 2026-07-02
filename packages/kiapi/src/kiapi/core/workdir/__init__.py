from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.create_work_dir import create_work_dir
    from ._settings import WorkDirSettings, settings_manager

__all__ = [
    "WorkDirSettings",
    "create_work_dir",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "WorkDirSettings": "._settings",
        "create_work_dir": "._helpers.create_work_dir",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
