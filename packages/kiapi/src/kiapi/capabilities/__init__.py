"""Family packages — one subpackage per family (dir == family).

Each family exposes a ``register()`` that populates the global model + help
registries (see core/model, core/help). Registration is explicit, not an import
side effect: the CLI bootstrap calls each family's ``register`` before starting
the API server or running setup/check commands.

Shared building blocks reused across families live here too: the common
request-error types and the Files-API path resolver.
"""

from ._exceptions.CapabilityError import CapabilityError
from ._exceptions.ValidationError import ValidationError
from ._helpers.attach_mflux_progress import attach_mflux_progress
from ._helpers.get_file_path import get_file_path
from ._helpers.resolve_file_ref import resolve_file_ref

__all__ = [
    "CapabilityError",
    "ValidationError",
    "attach_mflux_progress",
    "get_file_path",
    "resolve_file_ref",
]
