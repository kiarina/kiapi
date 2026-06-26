"""Video API (ltx2): ``POST /v1/video/ltx2/generate`` (JSON; sync or async)."""

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
from kiapi.capabilities.ltx2 import (
    GenerateRequest,
    ValidationError,
    detect_mode,
    handle_generate,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.video_response import VideoResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/video/ltx2/generate",
    responses=build_job_responses("video/mp4", result_model=VideoResponse),
)
async def generate(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate a short MP4 with LTX-2 distilled (text/image/audio to video).

    The mode is inferred from supplied inputs: prompt only is T2V; `image` adds
    first-frame I2V; `end_image` adds last-frame conditioning; `audio` drives A2V
    timing/motion; and `generate_audio=true` asks LTX-2 to synthesize audio. The
    same endpoint serves both `sync` and `async` via `mode`.

    Sync content negotiation: the job produces one MP4 artifact, so unless the
    client asks for JSON the raw video bytes are returned with
    `X-Kiapi-File-Id` / `X-Kiapi-Job-Id` headers. With
    `Accept: application/json` (or async), the Job JSON is returned, whose
    `result` follows VideoResponse.

    LTX-2 is a transient model: each call reserves the configured memory budget,
    loads the pipeline, generates, and frees it instead of keeping a resident
    model in `/health`. Async returns 202 immediately; poll
    GET /v1/jobs/{job_id} and fetch the artifact via GET /v1/files/{file_id}.
    """
    try:
        spec = model_registry.resolve("ltx2", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_generate(req, variant=spec.name, has_audio=req.audio is not None)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    mode = detect_mode(
        has_image=req.image is not None,
        has_end_image=req.end_image is not None,
        has_audio=req.audio is not None,
        generate_audio=req.generate_audio,
    )

    def thunk():  # type: ignore
        return handle_generate(ctx, req, mode)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="ltx2",
        params=req.gen_params() | {"model": spec.name, "mode_detected": mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="ltx2", base_path="/v1/video/ltx2")
