"""Image API (depthpro): ``POST /v1/image/depthpro/estimate``."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from kiapi.api import (
    REQUIRE_AUTH,
    build_job_responses,
    get_accept,
    get_ctx,
    get_worker,
    register_capability_endpoints,
    submit_and_maybe_wait,
)
from kiapi.capabilities.depthpro import (
    EstimateRequest,
    ValidationError,
    handle_estimate,
    validate_estimate,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.estimate_response import EstimateResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/image/depthpro/estimate",
    responses=build_job_responses("image/png", result_model=EstimateResponse),
)
async def estimate(
    req: EstimateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Estimate a depth map from one image (Depth Pro, image-to-depth).

    Produces a grayscale depth PNG (near = bright, far = dark) and, unless
    `include_depth_data` is false, a compressed NPZ holding the raw float depth
    array plus min/max depth. The same endpoint serves both `sync` and `async`
    via `mode`.

    Sync content negotiation: when exactly one artifact is produced (i.e.
    `include_depth_data=false`) and the client does not ask for JSON, the raw PNG
    bytes are returned with `X-Kiapi-File-Id` / `X-Kiapi-Job-Id` headers — so
    `curl -o depth.png` just works. Otherwise (JSON requested, two artifacts, or
    async) the Job JSON is returned, whose `result` follows EstimateResponse.

    A `quantize` value differing from the resident model runs a one-off transient
    model (slower, not reused). Async returns 202 immediately; poll
    GET /v1/jobs/{job_id} and fetch artifacts via GET /v1/files/{file_id}.
    """
    try:
        spec = model_registry.resolve("depthpro", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904

    try:
        validate_estimate(req)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_estimate(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="depthpro",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="depthpro", base_path="/v1/image/depthpro")
