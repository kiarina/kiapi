"""Sound-effect service entry: resolve → acquire (memory budget) → generate.

Body of the se job's worker-thread thunk. The handler writes its WAV artifact to
the global file store and returns metadata; the job's ``artifacts`` is the
produced file_id.
"""

from kiapi.core.app import AppContext
from kiapi.core.file import FileID
from kiapi.core.job import JobResult
from kiapi.core.model import model_registry

from .._settings import settings_manager
from .._views.generate_request import GenerateRequest
from .resolve_generate_params import resolve_generate_params


def handle_generate(
    ctx: AppContext, req: GenerateRequest
) -> tuple[JobResult, list[FileID]]:
    spec = model_registry.resolve("audiogen", req.model)
    ctx.ensure_model_ready(spec)
    settings = settings_manager.get_settings()
    params = resolve_generate_params(settings, req, variant=spec.name)
    payload = ctx.memory_manager.acquire(spec)
    result = spec.module.run(payload, params, ctx.file_store)
    return result, [result["file_id"]]
