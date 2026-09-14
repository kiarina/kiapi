from kiapi.capabilities.embedding import EmbedRequest, handle_embed
from kiapi.core.app import AppContext
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._operations.create_sample_image import create_sample_image
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    image_file_id = create_sample_image(ctx)
    rec = ctx.file_store.get(image_file_id)
    if rec is None:
        raise RuntimeError("failed to create check input image")
    result, artifacts = handle_embed(
        ctx,
        EmbedRequest(model=spec.name, image=rec.path),
    )
    return build_check_result(spec, result, artifacts)
