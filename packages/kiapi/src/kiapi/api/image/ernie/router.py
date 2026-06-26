"""Image API (ernie): ERNIE-Image generate/edit/train."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from kiapi.api import (
    REQUIRE_AUTH,
    build_job_responses,
    build_train_responses,
    get_accept,
    get_ctx,
    get_worker,
    register_capability_endpoints,
    submit_and_maybe_wait,
)
from kiapi.capabilities.ernie import (
    EditRequest,
    GenerateRequest,
    TrainRequest,
    ValidationError,
    handle_edit,
    handle_generate,
    handle_train,
    validate_edit,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.file import FileIDRef
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.image_response import ImageResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/image/ernie/generate",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def generate_ernie_endpoint(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate an image from a text prompt (ERNIE-Image, text-to-image).

    No input image — use `/v1/image/ernie/edit` for image-to-image. The same
    endpoint serves both `sync` and `async` via `mode`. Variant defaults differ:
    `turbo` (default) is fast and uses few steps; `base` is higher quality and
    slower.

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
        spec = model_registry.resolve("ernie", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_generate(req, variant=spec.name)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_generate(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="ernie",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


@router.post(
    "/v1/image/ernie/edit",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def edit_ernie_endpoint(
    req: EditRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Edit a single input image with a prompt (ERNIE-Image, image-to-image).

    Takes one `image` (FileRef) plus a `prompt`; `image_strength` controls how
    much of the input is preserved (lower = closer to input). Output must be
    square by default (a guard around an mflux 0.18.0 non-square img2img issue),
    overrideable via `KIAPI_ERNIE_EDIT_REQUIRE_SQUARE=0`. The same endpoint
    serves both `sync` and `async` via `mode`.

    Sync content negotiation, transient-model behavior (`loras` / `quantize`
    override), and the ImageResponse `result` shape match
    `/v1/image/ernie/generate`.
    """
    try:
        spec = model_registry.resolve("ernie", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    try:
        validate_edit(req, variant=spec.name)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    def thunk():  # type: ignore
        return handle_edit(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="ernie-edit",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


@router.post("/v1/image/ernie/train", responses=build_train_responses())
async def train_ernie_endpoint(
    req: TrainRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Train a LoRA adapter on a captioned image set (ERNIE-Image, always async).

    Long-running, so this endpoint is always async: it returns 202 with a
    job_id — poll GET /v1/jobs/{job_id}. The `dataset` is a Files-API ZIP whose
    images each have a same-stem `.txt` caption. On success the job's `result`
    holds `adapter_file_id` (the trained `.safetensors`, also the artifact),
    `adapter_bytes`, `num_images`, the resolved `config`, `lora_targets`, and
    `timings`; the adapter can then be passed back via `loras` on generate/edit.
    """
    try:
        spec = model_registry.resolve("ernie", req.model)
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    if (
        isinstance(req.dataset, FileIDRef)
        and ctx.file_store.get(req.dataset.file_id) is None
    ):
        raise HTTPException(
            status_code=400, detail=f"unknown dataset file_id {req.dataset.file_id!r}"
        )

    def thunk():  # type: ignore
        return handle_train(ctx, req)

    return await submit_and_maybe_wait(
        ctx,
        worker,
        type="ernie-train",
        params={
            "model": spec.name,
            "dataset": req.dataset.model_dump(mode="json"),
            "num_epochs": req.num_epochs,
            "lora_rank": req.lora_rank,
        },
        thunk=thunk,
        mode="async",
    )


register_capability_endpoints(router, name="ernie", base_path="/v1/image/ernie")
