"""Ideogram 4 text-to-image service entry (worker-thread thunk body)."""

from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._settings import settings_manager
from .._views.generate_request import GenerateRequest
from .is_quantize_override import is_quantize_override
from .resolve_generate_params import resolve_generate_params


def handle_generate(
    ctx: AppContext, req: GenerateRequest
) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("ideogram4", req.model)
    ctx.ensure_model_ready(spec)
    override = is_quantize_override(settings, req)
    params = resolve_generate_params(settings, req, variant=spec.name)

    if override:
        ctx.memory_manager.reserve(spec.weight_gb + spec.peak_headroom_gb)
        result = spec.module.run_generate_transient(spec, params, ctx.file_store)
    else:
        payload = ctx.memory_manager.acquire(spec)
        result = spec.module.run_generate(payload, params, ctx.file_store)

    return result, [result["file_id"]]
