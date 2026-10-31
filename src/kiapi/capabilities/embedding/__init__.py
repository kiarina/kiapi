"""Embedding capability — multi-model text/image embeddings via mlx-embeddings.

Integrates mlx-embedding-server: served from the shared single-flight worker
under the global memory budget. The `model` field selects which model answers.
The request and response follow OpenAI's embeddings API. Sync only.

These are small models that agents call frequently, so they get a positive
``priority`` (higher = kept longer): they survive eviction churn from big chat /
generation models, which is exactly the intended use of priority.
``weight_gb`` / ``peak_headroom_gb`` are seeded from the original server's
estimates and reconciled with on-device measurement at load.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._helpers.register import register
    from ._operations.handle_embed import handle_embed
    from ._settings import settings_manager
    from ._views.embed_request import EmbedItem, EmbedRequest

__all__ = [
    "EmbedItem",
    "EmbedRequest",
    "handle_embed",
    "register",
    "settings_manager",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__} has no attribute {name}")

    module_map = {
        "EmbedItem": "._views.embed_request",
        "EmbedRequest": "._views.embed_request",
        "handle_embed": "._operations.handle_embed",
        "register": "._helpers.register",
        "settings_manager": "._settings",
    }

    globals()[name] = getattr(import_module(module_map[name], __name__), name)
    return globals()[name]
