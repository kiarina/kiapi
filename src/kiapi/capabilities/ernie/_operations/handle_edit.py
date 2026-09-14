"""ERNIE-Image single-image edit service entry (worker-thread thunk body)."""

from kiapi.capabilities import get_file_path
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._settings import settings_manager
from .._views.edit_request import EditRequest
from .is_quantize_override import is_quantize_override
from .resolve_edit_params import resolve_edit_params
from .resolve_lora_params import resolve_lora_params


def handle_edit(ctx: AppContext, req: EditRequest) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("ernie", req.model)
    ctx.ensure_model_ready(spec)
    image_path = get_file_path(ctx.file_store, req.image, kind="image")
    lora_params = resolve_lora_params(ctx, req.loras)
    override = is_quantize_override(settings, req, variant=spec.name)
    params = resolve_edit_params(
        settings, req, variant=spec.name, image_path=image_path
    )

    if lora_params.paths or override:
        ctx.memory_manager.reserve(spec.weight_gb + spec.peak_headroom_gb)
        result = spec.module.run_edit_transient(
            spec,
            params,
            ctx.file_store,
            lora_paths=lora_params.paths,
            lora_scales=lora_params.scales,
        )
    else:
        payload = ctx.memory_manager.acquire(spec)
        result = spec.module.run_edit(payload, params, ctx.file_store)
    return result, [result["file_id"]]
