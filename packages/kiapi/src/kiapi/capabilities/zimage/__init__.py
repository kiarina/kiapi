"""zimage family - Z-Image text-to-image generation via mflux.

Endpoint: ``POST /v1/image/zimage/generate`` (multipart params; txt2img).
Integrates mflux's Z-Image. Two variants:

  - ``turbo`` (default) - distilled few-step model, pre-quantized 4-bit, fast.
  - ``base`` - full Z-Image, more steps + guidance, higher quality / slower.

Both are resident MLX models held under the global budget. A request that adds
``loras`` or overrides ``quantize`` is served by a one-off transient model
(mflux bakes those in at load time) via ``memory.reserve()`` instead. Sync/async
via ``mode``; the PNG lands in the Files API.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kiapi.capabilities import ValidationError

    from ._helpers.register import register
    from ._helpers.validate_generate import validate_generate
    from ._operations.handle_generate import handle_generate
    from ._operations.handle_train import handle_train
    from ._settings import settings_manager
    from ._views.generate_request import GenerateRequest
    from ._views.train_request import TrainRequest

__all__ = [
    "GenerateRequest",
    "TrainRequest",
    "ValidationError",
    "handle_generate",
    "handle_train",
    "register",
    "settings_manager",
    "validate_generate",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "GenerateRequest": "._views.generate_request",
        "TrainRequest": "._views.train_request",
        "ValidationError": "kiapi.capabilities",
        "handle_generate": "._operations.handle_generate",
        "handle_train": "._operations.handle_train",
        "register": "._helpers.register",
        "settings_manager": "._settings",
        "validate_generate": "._helpers.validate_generate",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
