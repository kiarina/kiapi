"""Chat capability — OpenAI-compatible chat completions via mlx-vlm.

Integrates mlx-vlm-server: multiple Qwen vision/omni models served from the
shared single-flight worker under the global memory budget. The ``model`` field
selects which model answers; text + image (+ audio + video on omni) in, text
and/or tool calls out. Non-streaming and OpenAI-style SSE streaming are supported.

``register()`` registers its models and capability OpenAPI metadata.
``weight_gb`` / ``peak_headroom_gb`` are seeded from on-device measurement
(Mac Studio M4 Max, 2026-06): omni weights ~20.3 GB, qwen3.8-27b ~16.0 GB;
qwen3.8-flash-next ~79.5 GB with its PLE table memory-mapped (2026-09).
All chat models reserve their configured APC capacity plus a 4 GiB generation
margin. Idle models also report retained APC bytes to the global memory budget.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.register import register
    from ._operations.handle_chat import handle_chat
    from ._settings import settings_manager
    from ._utils.read_context_window import read_context_window
    from ._views.chat_request import ChatRequest

__all__ = [
    "ChatRequest",
    "handle_chat",
    "read_context_window",
    "register",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "ChatRequest": "._views.chat_request",
        "handle_chat": "._operations.handle_chat",
        "read_context_window": "._utils.read_context_window",
        "register": "._helpers.register",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
