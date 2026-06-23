"""ACE-Step extract service entry (worker-thread thunk body)."""

from kiapi.capabilities import resolve_file_ref
from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult

from .._views.extract_request import ExtractRequest
from .resolve_engine import resolve_engine
from .resolve_extract_params import resolve_extract_params


def handle_extract(
    ctx: AppContext, req: ExtractRequest
) -> tuple[JobResult, list[FileID]]:
    spec, module, engine = resolve_engine(ctx, req.model)
    source = resolve_file_ref(ctx.file_store, req.source, kind="source")

    stems = []
    artifacts = []
    for target in req.targets:
        params = resolve_extract_params(
            req,
            variant=spec.name,
            source_file_id=source.file_id,
            src_audio=source.path,
            target=target,
        )
        res = module.generate_track(engine, params, ctx.file_store)
        stems.append(res)
        artifacts.append(res["file_id"])

    return {
        "task": "extract",
        "source_file_id": source.file_id,
        "targets": req.targets,
        "stems": stems,
    }, artifacts
