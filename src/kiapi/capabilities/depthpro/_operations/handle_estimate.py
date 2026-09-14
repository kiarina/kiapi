"""Depth Pro service entry: resolve input image → run resident/transient model.

Body of the depthpro job's worker-thread thunk. Stores the depth PNG (and an
optional NPZ of the raw depth array) in the global file store; the job's
``artifacts`` is the produced file_id(s).
"""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult, creep_progress
from kiapi.core.model import model_registry

from .._helpers.validate_estimate import validate_estimate
from .._settings import settings_manager
from .._views.estimate_request import EstimateRequest
from .is_quantize_override import is_quantize_override
from .resolve_estimate_params import resolve_estimate_params


def handle_estimate(
    ctx: AppContext, req: EstimateRequest
) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("depthpro", req.model)
    ctx.ensure_model_ready(spec)
    image = resolve_file_ref(ctx.file_store, req.image, kind="image")
    validate_estimate(req, image_path=image.path)
    override = is_quantize_override(settings, req)
    params = resolve_estimate_params(
        settings,
        req,
        variant=spec.name,
        image_file_id=image.file_id,
        image_path=image.path,
    )

    if override:
        ctx.memory_manager.reserve(spec.weight_gb + spec.peak_headroom_gb)
        with creep_progress(eta_s=settings.progress_eta_s):
            result = spec.module.run_transient(spec, params, ctx.file_store)
    else:
        payload = ctx.memory_manager.acquire(spec)
        with creep_progress(eta_s=settings.progress_eta_s):
            result = spec.module.run(payload, params, ctx.file_store)

    artifacts = [result["depth_image_file_id"]]
    if result.get("depth_data_file_id") is not None:
        artifacts.append(result["depth_data_file_id"])
    return result, artifacts
