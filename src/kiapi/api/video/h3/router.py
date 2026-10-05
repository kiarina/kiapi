"""Video API (h3): ``POST /v1/video/h3/generate`` (JSON; sync or async)."""

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
from kiapi.capabilities.h3 import (
    GenerateRequest,
    ValidationError,
    handle_generate,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.video_response import VideoResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/video/h3/generate",
    responses=build_job_responses("video/mp4", result_model=VideoResponse),
)
async def generate(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate an MP4 with stereo audio from text and ordered references.

    `images`, `videos` and `audios` are referred to in the prompt as
    `<Picture N>`, `<Video N>` and `<Audio N>`. Without references the model
    generates from text alone.

    A run takes tens of minutes, so the default `mode` is `async`: it returns
    202 immediately; poll GET /v1/jobs/{job_id} and fetch the artifact via
    GET /v1/files/{file_id}. With `sync` and `Accept` other than JSON, the raw
    MP4 is returned with `X-Kiapi-File-Id` / `X-Kiapi-Job-Id` headers; the
    Job JSON `result` follows VideoResponse.
    """
    try:
        spec = model_registry.resolve("h3", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_generate(req)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_generate(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="h3",
        params=req.gen_params() | {"model": spec.name},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="h3", base_path="/v1/video/h3")
