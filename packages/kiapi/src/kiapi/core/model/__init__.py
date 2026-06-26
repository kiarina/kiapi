"""The model registry: the catalog of servable models across all families.

Public surface (unchanged from the former ``core/model.py``):

  - :class:`ModelSpec` — a registry entry (variant + family/domain + repo +
    handler module + memory/budget metadata).
  - :class:`ModelRegistry` / the ``model_registry`` singleton — register,
    list, group, and resolve specs.
  - :class:`UnknownModelError` — raised by ``resolve`` on an unknown ``model``.

The semantic axes are spelled out as types in :mod:`._types`
(``ModelName`` / ``ModelFamily`` / ``ModelDomain`` / ``ModelRepo``).
"""

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
