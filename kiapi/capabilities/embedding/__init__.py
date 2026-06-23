"""Embedding capability — multi-model text/image embeddings via mlx-embeddings.

Integrates mlx-embedding-server: served from the shared single-flight worker
under the global memory budget. The `model` field selects which model answers;
one item per request with one field per modality. Sync only.

These are small models that agents call frequently, so they get a positive
``priority`` (higher = kept longer): they survive eviction churn from big chat /
generation models, which is exactly the intended use of priority.
``weight_gb`` / ``peak_headroom_gb`` are seeded from the original server's
estimates and reconciled with on-device measurement at load.
"""

from ._helpers.register import register
from ._operations.handle_embed import handle_embed
from ._settings import settings_manager
from ._views.embed_request import EmbedRequest

__all__ = [
    "EmbedRequest",  # ._views
    "handle_embed",  # ._operations
    "register",  # ._helpers
    "settings_manager",  # ._settings
]
