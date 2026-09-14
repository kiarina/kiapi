"""Image API (zimage): ``POST /v1/image/zimage/generate`` (JSON; sync or async)."""

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
from kiapi.capabilities.zimage import (
    GenerateRequest,
    TrainRequest,
    ValidationError,
    handle_generate,
    handle_train,
    validate_generate,
)
from kiapi.core.app import AppContext
from kiapi.core.file import FileIDRef
from kiapi.core.model import UnknownModelError, model_registry
from kiapi.core.worker import Worker

from ._views.image_response import ImageResponse

router = APIRouter(dependencies=REQUIRE_AUTH)


@router.post(
    "/v1/image/zimage/generate",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def generate_image_endpoint(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate an image from a text prompt (Z-Image, text-to-image).

    No input image — Z-Image is txt2img only. The same endpoint serves both
    `sync` and `async` via `mode`. Variant defaults differ: `turbo` (default) is
    distilled, few-step and fast; `base` is the full model — more steps and
    guidance, higher quality but slower.

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
        spec = model_registry.resolve("zimage", req.model)
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
        type="zimage",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


@router.post("/v1/image/zimage/train", responses=build_train_responses())
async def train_zimage_endpoint(
    req: TrainRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Train a LoRA adapter on a captioned image set (Z-Image, always async).

    Long-running, so this endpoint is always async: it returns 202 with a
    job_id — poll GET /v1/jobs/{job_id}. The `dataset` is a Files-API ZIP whose
    images each have a same-stem `.txt` caption. On success the job's `result`
    holds `adapter_file_id` (the trained `.safetensors`, also the artifact),
    `adapter_bytes`, `num_images`, the resolved `config`, `lora_targets`,
    `checkpoint`, and `timings`; the adapter can then be passed back via `loras`
    on generate."""
    try:
        spec = model_registry.resolve("zimage", req.model)
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
        type="zimage-train",
        params={
            "model": spec.name,
            "dataset": req.dataset.model_dump(mode="json"),
            "num_epochs": req.num_epochs,
            "lora_rank": req.lora_rank,
        },
        thunk=thunk,
        mode="async",
    )


register_capability_endpoints(router, name="zimage", base_path="/v1/image/zimage")
