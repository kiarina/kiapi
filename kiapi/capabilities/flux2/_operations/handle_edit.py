"""FLUX.2 multi-reference edit service entry (worker-thread thunk body)."""

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
from .role_spec import role_spec


def handle_edit(ctx: AppContext, req: EditRequest) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    base_spec = model_registry.resolve("flux2", req.model)
    ctx.ensure_model_ready(base_spec)
    spec = role_spec(base_spec, "edit")
    image_paths = [
        get_file_path(ctx.file_store, image, kind="image") for image in req.images
    ]
    lora_params = resolve_lora_params(ctx, req.loras)
    override = is_quantize_override(settings, req, variant=base_spec.name)
    params = resolve_edit_params(
        settings, req, variant=base_spec.name, image_paths=image_paths
    )

    if lora_params.paths or override:
        ctx.memory_manager.reserve(base_spec.weight_gb + base_spec.peak_headroom_gb)
        result = base_spec.module.run_edit_transient(
            base_spec,
            params,
            ctx.file_store,
            lora_paths=lora_params.paths,
            lora_scales=lora_params.scales,
        )
    else:
        payload = ctx.memory_manager.acquire(spec)
        result = spec.module.run_edit(payload, params, ctx.file_store)

    return result, [result["file_id"]]
