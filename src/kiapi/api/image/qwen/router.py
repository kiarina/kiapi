"""Image API (qwen): Qwen Image generate/edit."""

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
from kiapi.capabilities.qwen import (
    EditRequest,
    GenerateRequest,
    ValidationError,
    handle_edit,
    handle_generate,
    validate_edit,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.image_response import ImageResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/image/qwen/generate",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def generate_qwen_endpoint(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate an image from a text prompt (Qwen Image, text-to-image / img2img).

    Plain text-to-image by default; supply `init_image` (+ optional
    `image_strength`) to run img2img instead — use `/v1/image/qwen/edit` for
    natural-language single/multi-image editing. The same endpoint serves both
    `sync` and `async` via `mode`. This endpoint only accepts the `image` model
    variant.

    Sync content negotiation: a single image is produced, so unless the client
    asks for JSON the raw image bytes are returned with `X-Kiapi-File-Id` /
    `X-Kiapi-Job-Id` headers — `curl -o out.png` just works. With
    `Accept: application/json` (or async) the Job JSON is returned, whose
    `result` follows ImageResponse.

    Any `loras` or a `quantize` differing from the resident model runs a one-off
    transient model (slower, not reused). Async returns 202 immediately; poll
    GET /v1/jobs/{job_id} and fetch the artifact via GET /v1/files/{file_id}.
    """
    try:
        spec = model_registry.resolve("qwen", req.model or "image")
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    if spec.name != "image":
        raise HTTPException(
            status_code=400, detail="qwen generate requires model 'image'"
        )
    try:
        validate_generate(req)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_generate(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="qwen",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


@router.post(
    "/v1/image/qwen/edit",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def edit_qwen_endpoint(
    req: EditRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Edit / combine one or more reference images with a prompt (Qwen Image Edit).

    Takes a list of `images` (FileRefs, single or multi-image) plus a
    natural-language `prompt`. For plain image-to-image from a single seed image,
    use `init_image` on `/v1/image/qwen/generate` instead. The same endpoint
    serves both `sync` and `async` via `mode`. This endpoint only accepts the
    `edit-2509` model variant.

    Sync content negotiation, transient-model behavior (`loras` / `quantize`
    override), and the ImageResponse `result` shape match
    `/v1/image/qwen/generate`.
    """
    try:
        spec = model_registry.resolve("qwen", req.model or "edit-2509")
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    if spec.name != "edit-2509":
        raise HTTPException(
            status_code=400, detail="qwen edit requires model 'edit-2509'"
        )
    try:
        validate_edit(req)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_edit(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="qwen-edit",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


register_capability_endpoints(router, name="qwen", base_path="/v1/image/qwen")
