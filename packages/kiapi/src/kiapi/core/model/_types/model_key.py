from .model_alias import ModelAlias
from .model_name import ModelName
from .model_repo import ModelRepo

type ModelKey = ModelName | ModelRepo | ModelAlias
"""A lookup token a request may use to address a model within its family — any of
the spec's ``name``, ``repo``, or ``aliases``. The registry indexes specs by
``(family, key.lower())``, so resolution is case-insensitive."""
