"""Derive a role-specific ModelSpec (its repo carries a ``#<role>`` marker).

The edit role loads a different mflux class than generate, so edit acquires a
resident model under a spec whose repo is tagged with the role.
"""

from kiapi.core.model import ModelSpec


def role_spec(spec: ModelSpec, role: str) -> ModelSpec:
    if role == "generate":
        return spec
    return spec.model_copy(update={"repo": f"{spec.repo}#{role}"})
