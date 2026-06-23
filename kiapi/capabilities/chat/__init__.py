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

from ._helpers.register import register
from ._operations.handle_chat import handle_chat
from ._settings import settings_manager
from ._views.chat_request import ChatRequest

__all__ = [
    "ChatRequest",  # ._views
    "handle_chat",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
]
