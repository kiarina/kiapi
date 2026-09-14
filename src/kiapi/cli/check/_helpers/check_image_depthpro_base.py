from kiapi.capabilities.depthpro import EstimateRequest, handle_estimate
from kiapi.core.app import AppContext
from kiapi.core.file import FileIDRef
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._operations.create_sample_image import create_sample_image
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    image_file_id = create_sample_image(ctx)
    result, artifacts = handle_estimate(
        ctx,
        EstimateRequest(
            model=spec.name,
            image=FileIDRef(file_id=image_file_id),
            include_depth_data=False,
        ),
    )
    return build_check_result(spec, result, artifacts)
