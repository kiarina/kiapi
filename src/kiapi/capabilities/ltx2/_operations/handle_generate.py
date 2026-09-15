"""LTX-2 generate service entry (worker-thread thunk body)."""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult, creep_progress
from kiapi.core.model import model_registry

from .._constants.variants import LTX25_VARIANT
from .._settings import LTX2Settings, settings_manager
from .._views.generate_params import GenerateParams
from .._views.generate_request import GenerateRequest
from .resolve_generate_params import resolve_generate_params


def handle_generate(
    ctx: AppContext,
    req: GenerateRequest,
    mode: str,
) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("ltx2", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_generate_params(settings, req, variant=spec.name)
    staged = _resolve_staged_inputs(ctx, req)

    ctx.memory_manager.reserve(spec.weight_gb + spec.peak_headroom_gb)

    with creep_progress(eta_s=_calc_eta_s(params, settings)):
        result = spec.module.run_generate(
            params, settings, ctx.file_store, staged, mode
        )

    return result, [result["file_id"]]


def _resolve_staged_inputs(ctx: AppContext, req: GenerateRequest) -> dict[str, str]:
    staged: dict[str, str] = {}
    if req.image is not None:
        staged["image"] = resolve_file_ref(ctx.file_store, req.image, kind="image").path
    if req.end_image is not None:
        staged["end_image"] = resolve_file_ref(
            ctx.file_store, req.end_image, kind="end_image"
        ).path
    if req.audio is not None:
        staged["audio"] = resolve_file_ref(ctx.file_store, req.audio, kind="audio").path
    return staged


def _calc_eta_s(params: GenerateParams, settings: LTX2Settings) -> float:
    if params.model != LTX25_VARIANT:
        base_s = settings.progress_eta_base_s
    else:
        base_s = settings.ltx25_progress_eta_base_s
        # Ratios measured at 768x512 / 121 frames against conv distilled.
        if params.pipeline == "dfr":
            base_s *= 1.75
        if params.video_decoder == "diffusion":
            base_s *= 1.6
    # Auto duration is unknown until the model predicts it; ~5 s is typical.
    num_frames = params.num_frames if params.num_frames is not None else 121
    frames = num_frames / 97
    pixels = (params.width * params.height) / (512 * 512)
    return base_s * max(frames * pixels, 0.1)
