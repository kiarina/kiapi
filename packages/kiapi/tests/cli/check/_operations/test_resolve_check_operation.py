from kiarina.utils.app import configure

from kiapi.cli import register_all_capabilities
from kiapi.cli.check.cli import _resolve_check_operation
from kiapi.core.model import model_registry


def test_resolve_check_operation_for_all_registered_models() -> None:
    # Capability registration resolves user directories, so set the app identity
    # first (the CLI reset fixture leaves it unconfigured for a clean slate).
    configure("kiapi", "kiarina")
    register_all_capabilities()

    missing = []
    for spec in model_registry.list_specs():
        try:
            _resolve_check_operation(spec)
        except ModuleNotFoundError:
            missing.append(f"{spec.domain}/{spec.family}/{spec.name}")

    assert missing == []
