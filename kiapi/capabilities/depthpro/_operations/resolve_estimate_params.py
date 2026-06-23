"""Merge an estimate request with settings defaults into the complete EstimateParams."""

from .._settings import DepthProSettings
from .._views.estimate_params import EstimateParams
from .._views.estimate_request import EstimateRequest


def resolve_estimate_params(
    settings: DepthProSettings,
    req: EstimateRequest,
    *,
    variant: str,
    image_file_id: str,
    image_path: str,
) -> EstimateParams:
    return EstimateParams(
        model=variant,
        image_file_id=image_file_id,
        image_path=image_path,
        quantize=req.quantize
        if req.quantize is not None
        else settings.default_quantize,
        include_depth_data=req.include_depth_data,
    )
