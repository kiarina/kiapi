"""The model registry: the catalog of servable models across all families.

The semantic axes are spelled out as types in :mod:`._types`
(``ModelName`` / ``ModelFamily`` / ``ModelDomain`` / ``ModelRepo``).
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._exceptions.unknown_model_error import UnknownModelError
    from ._schemas.model_spec import ModelSpec
    from ._services.model_registry import ModelRegistry, model_registry
    from ._types.model_alias import ModelAlias
    from ._types.model_domain import ModelDomain
    from ._types.model_family import ModelFamily
    from ._types.model_key import ModelKey
    from ._types.model_name import ModelName
    from ._types.model_repo import ModelRepo

__all__ = [
    "ModelAlias",
    "ModelDomain",
    "ModelFamily",
    "ModelKey",
    "ModelName",
    "ModelRegistry",
    "ModelRepo",
    "ModelSpec",
    "UnknownModelError",
    "model_registry",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "ModelAlias": "._types.model_alias",
        "ModelDomain": "._types.model_domain",
        "ModelFamily": "._types.model_family",
        "ModelKey": "._types.model_key",
        "ModelName": "._types.model_name",
        "ModelRegistry": "._services.model_registry",
        "ModelRepo": "._types.model_repo",
        "ModelSpec": "._schemas.model_spec",
        "UnknownModelError": "._exceptions.unknown_model_error",
        "model_registry": "._services.model_registry",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
