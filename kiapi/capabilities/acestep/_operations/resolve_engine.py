from typing import Any

from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec, model_registry


def resolve_engine(ctx: AppContext, model: str) -> tuple[ModelSpec, Any, object]:
    spec = model_registry.resolve("acestep", model)
    ctx.ensure_model_ready(spec)
    return spec, spec.module, ctx.memory_manager.acquire(spec)
