"""MiniMax H3 generate service entry (worker-thread thunk body)."""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID, FileRef
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry
from kiapi.core.workdir import create_work_dir

from .._settings import settings_manager
from .._views.generate_request import GenerateRequest
from .enhance_prompt import enhance_prompt
from .resolve_generate_params import resolve_generate_params


def handle_generate(
    ctx: AppContext,
    req: GenerateRequest,
) -> tuple[JobResult, list[FileID]]:
    settings = settings_manager.get_settings()
    spec = model_registry.resolve("h3", req.model)
    ctx.ensure_model_ready(spec)
    params = resolve_generate_params(settings, req, variant=spec.name)
    staged = {
        "images": _stage(ctx, req.images, "image"),
        "videos": _stage(ctx, req.videos, "video"),
        "audios": _stage(ctx, req.audios, "audio"),
    }

    prompt = enhance_prompt(
        ctx, params, staged, settings, create_work_dir("video/h3/enhance")
    )
    params = params.model_copy(update={"prompt": prompt})

    ctx.memory_manager.reserve(spec.weight_gb + spec.peak_headroom_gb)
    result = spec.module.run_generate(
        params, settings, ctx.file_store, staged, request_prompt=req.prompt
    )

    return result, [result["file_id"]]


def _stage(ctx: AppContext, refs: list[FileRef], kind: str) -> list[str]:
    return [
        resolve_file_ref(ctx.file_store, ref, kind=f"{kind}s[{i}]").path
        for i, ref in enumerate(refs)
    ]
