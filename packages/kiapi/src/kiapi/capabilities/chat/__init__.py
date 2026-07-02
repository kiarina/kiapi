"""Chat capability — OpenAI-compatible chat completions via mlx-vlm.

Integrates mlx-vlm-server: multiple Qwen vision/omni models served from the
shared single-flight worker under the global memory budget. The ``model`` field
selects which model answers; text + image (+ audio + video on omni) in, text
and/or tool calls out. Non-streaming and OpenAI-style SSE streaming are supported.

``register()`` registers its models and capability OpenAPI metadata.
``weight_gb`` / ``peak_headroom_gb`` are seeded from on-device measurement
(Mac Studio M4 Max, 2026-06): omni weights ~20.3 GB, qwen3.6-27b ~15.0 GB; the
generation peak over weights was negligible for text and single-image inputs, so
headroom is a conservative margin for heavy multimodal (video) inputs.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.register import register
    from ._operations.handle_chat import handle_chat
    from ._settings import settings_manager
    from ._views.chat_request import ChatRequest

__all__ = [
    "ChatRequest",
    "handle_chat",
    "register",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "ChatRequest": "._views.chat_request",
        "handle_chat": "._operations.handle_chat",
        "register": "._helpers.register",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
