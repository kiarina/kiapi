"""ACE-Step generate service entry (worker-thread thunk body)."""

from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult

from .._views.generate_request import GenerateRequest
from .resolve_engine import resolve_engine
from .resolve_generate_params import resolve_generate_params


def handle_generate(
    ctx: AppContext, req: GenerateRequest
) -> tuple[JobResult, list[FileID]]:
    spec, module, engine = resolve_engine(ctx, req.model)
    params = resolve_generate_params(req, variant=spec.name)
    result = module.generate_track(engine, params, ctx.file_store)
    return result, [result["file_id"]]
