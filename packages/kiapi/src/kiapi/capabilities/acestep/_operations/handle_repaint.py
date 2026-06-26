"""ACE-Step repaint service entry (worker-thread thunk body)."""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult

from .._views.repaint_request import RepaintRequest
from .resolve_engine import resolve_engine
from .resolve_repaint_params import resolve_repaint_params


def handle_repaint(
    ctx: AppContext, req: RepaintRequest
) -> tuple[JobResult, list[FileID]]:
    spec, module, engine = resolve_engine(ctx, req.model)
    source = resolve_file_ref(ctx.file_store, req.source, kind="source")
    params = resolve_repaint_params(
        req,
        variant=spec.name,
        source_file_id=source.file_id,
        src_audio=source.path,
    )
    result = module.generate_track(engine, params, ctx.file_store)
    return result, [result["file_id"]]
