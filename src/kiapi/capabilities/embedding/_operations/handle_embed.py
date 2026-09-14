"""Embedding service entry: resolve → acquire (memory budget) → run.

Body of the embedding job's worker-thread thunk. Mirrors mlx-embedding-server's
Engine.run, but loads through the *global* memory manager so embedding models
share the budget with every other capability.
"""

from kiapi.core.app import AppContext
from kiapi.core.model import model_registry

from .._settings import settings_manager
from .._views.embed_request import EmbedRequest
from .resolve_embed_params import resolve_embed_params


def handle_embed(ctx: AppContext, req: EmbedRequest) -> tuple[dict, list[str]]:
    """Run one embedding. Returns (embedding_result, artifact_file_ids)."""
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("embedding", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_embed_params(settings, req, variant=spec.name)
    payload = ctx.memory_manager.acquire(spec)
    result = spec.module.run(payload, params)
    return result, []  # embeddings produce no file artifacts
