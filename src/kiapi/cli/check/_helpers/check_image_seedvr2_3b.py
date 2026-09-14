from kiapi.capabilities.seedvr2 import UpscaleRequest, handle_upscale
from kiapi.core.app import AppContext
from kiapi.core.file import FileIDRef
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._operations.create_sample_image import create_sample_image
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    image_file_id = create_sample_image(ctx, size=128)
    result, artifacts = handle_upscale(
        ctx,
        UpscaleRequest(
            model=spec.name,
            image=FileIDRef(file_id=image_file_id),
            resolution="2x",
            seed=1,
            quality=90,
        ),
    )
    return build_check_result(spec, result, artifacts)
