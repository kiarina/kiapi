from kiarina.utils.component_registry import ComponentRegistry

from .._settings import settings_manager
from .._types.relay import Relay

relay_registry = ComponentRegistry[Relay](
    expected_type=Relay,  # type: ignore[type-abstract]
    component_label="Relay",
    get_default=lambda: settings_manager.get_settings().default,
    get_presets=lambda: settings_manager.get_settings().presets,
    get_customs=lambda: settings_manager.get_settings().customs,
)
