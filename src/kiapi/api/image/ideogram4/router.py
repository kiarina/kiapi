"""Image API (ideogram4): Ideogram 4 txt2img."""

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
from kiapi.capabilities.ideogram4 import (
    GenerateRequest,
    ValidationError,
    handle_generate,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.image_response import ImageResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/image/ideogram4/generate",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def generate(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate one image from a text prompt or JSON caption (Ideogram 4, text-to-image).

    Ideogram 4 is typography-focused txt2img — there is no image-to-image or
    training. Prefer a structured JSON `prompt` (high_level_description,
    optional style_description, compositional_deconstruction with element
    `bbox`/`text`) for crisp lettering; plain text works but is usually weaker.
    The same endpoint serves both `sync` and `async` via `mode`. Pick the
    speed/quality tradeoff with `preset` (V4_TURBO_12 → V4_DEFAULT_20 →
    V4_QUALITY_48).

    Sync content negotiation: a single image is produced, so unless the client
    asks for JSON the raw image bytes are returned with `X-Kiapi-File-Id` /
    `X-Kiapi-Job-Id` headers — `curl -o out.png` just works. With
    `Accept: application/json` (or async) the Job JSON is returned, whose
    `result` follows ImageResponse.

    A `quantize` differing from the resident model runs a one-off transient
    model (slower, not reused). Ideogram 4 may return an 'Image blocked by safety
    filter' image (including false positives); kiapi stores it as the artifact
    rather than raising an error. Async returns 202 immediately; poll
    GET /v1/jobs/{job_id} and fetch the artifact via GET /v1/files/{file_id}.
    """
    try:
        spec = model_registry.resolve("ideogram4", req.model)
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
        type="ideogram4",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="ideogram4", base_path="/v1/image/ideogram4")
