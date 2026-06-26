"""SeedVR2 service entry: resolve input image → run resident/transient model.

Body of the seedvr2 job's worker-thread thunk. Stores the upscaled image in the
global file store; the job's ``artifacts`` is the produced file_id.
"""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._settings import settings_manager
from .._views.upscale_request import UpscaleRequest
from .is_quantize_override import is_quantize_override
from .resolve_upscale_params import resolve_upscale_params


def handle_upscale(
    ctx: AppContext, req: UpscaleRequest
) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("seedvr2", req.model)
    ctx.ensure_model_ready(spec)
    image = resolve_file_ref(ctx.file_store, req.image, kind="image")
    override = is_quantize_override(settings, req)
    params = resolve_upscale_params(
        settings,
        req,
        variant=spec.name,
        image_file_id=image.file_id,
        image_path=image.path,
    )

    if override:
        ctx.memory_manager.reserve(spec.weight_gb + spec.peak_headroom_gb)
        result = spec.module.run_transient(spec, params, ctx.file_store)
    else:
        payload = ctx.memory_manager.acquire(spec)
        result = spec.module.run(payload, params, ctx.file_store)

    return result, [result["file_id"]]
