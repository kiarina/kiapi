"""ACE-Step cover service entry (worker-thread thunk body)."""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult

from .._views.cover_request import CoverRequest
from .resolve_cover_params import resolve_cover_params
from .resolve_engine import resolve_engine


def handle_cover(ctx: AppContext, req: CoverRequest) -> tuple[JobResult, list[FileID]]:
    spec, module, engine = resolve_engine(ctx, req.model)
    source = resolve_file_ref(ctx.file_store, req.source, kind="source")
    params = resolve_cover_params(
        req,
        variant=spec.name,
        source_file_id=source.file_id,
        src_audio=source.path,
    )
    result = module.generate_track(engine, params, ctx.file_store)
    return result, [result["file_id"]]
