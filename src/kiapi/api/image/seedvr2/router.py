"""Image API (seedvr2): ``POST /v1/image/seedvr2/upscale``."""

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
from kiapi.capabilities.seedvr2 import (
    UpscaleRequest,
    ValidationError,
    handle_upscale,
    validate_upscale,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.image_response import ImageResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/image/seedvr2/upscale",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def upscale_seedvr2_endpoint(
    req: UpscaleRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Upscale one image with diffusion super-resolution (SeedVR2 via mflux).

    Takes an input `image` (FileRef) and produces a higher-resolution version.
    SeedVR2 is super-resolution, not prompt-driven generation — there is no
    prompt. The target size is set by `resolution`: an integer shortest-edge
    pixel target (16..2048) or a scale factor like `"2x"` (up to `4.0x`). The
    same endpoint serves both `sync` and `async` via `mode`.

    Sync content negotiation: a single image is produced, so unless the client
    asks for JSON the raw image bytes are returned with `X-Kiapi-File-Id` /
    `X-Kiapi-Job-Id` headers — `curl -o out.png` just works. With
    `Accept: application/json` (or async) the Job JSON is returned, whose
    `result` follows ImageResponse.

    A `quantize` differing from the resident model's quantization runs a one-off
    transient model (slower, not reused). Async returns 202 immediately; poll
    GET /v1/jobs/{job_id} and fetch the artifact via GET /v1/files/{file_id}.
    """
    try:
        spec = model_registry.resolve("seedvr2", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_upscale(req)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_upscale(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="seedvr2",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="seedvr2", base_path="/v1/image/seedvr2")
