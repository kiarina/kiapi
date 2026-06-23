from kiapi.core.app import AppContext
from kiapi.core.file import FileIDRef
from kiapi.core.model import ModelSpec

from .._operations.build_check_result import build_check_result
from .._operations.create_sample_image import create_sample_image
from .._schemas.check_result import CheckResult


def check(ctx: AppContext, spec: ModelSpec) -> CheckResult:
    from kiapi.capabilities.qwen import EditRequest, handle_edit

    image_file_id = create_sample_image(ctx)
    result, artifacts = handle_edit(
        ctx,
        EditRequest(
            model=spec.name,
            prompt="make the object blue, keep the simple composition",
            images=[FileIDRef(file_id=image_file_id)],
            width=256,
            height=256,
            steps=1,
            seed=1,
            quality=90,
        ),
    )
    return build_check_result(spec, result, artifacts)
