from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.dedupe_resources import dedupe_resources
    from ._helpers.register_all_capabilities import register_all_capabilities
    from ._helpers.run_resources import run_resources
    from ._helpers.select_specs import select_specs

__all__ = [
    "dedupe_resources",
    "register_all_capabilities",
    "run_resources",
    "select_specs",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "dedupe_resources": "._helpers.dedupe_resources",
        "register_all_capabilities": "._helpers.register_all_capabilities",
        "run_resources": "._helpers.run_resources",
        "select_specs": "._helpers.select_specs",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
