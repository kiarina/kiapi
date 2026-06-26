"""Image API (flux2): FLUX.2 generate/edit/train."""

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
from kiapi.capabilities.flux2 import (
    EditRequest,
    GenerateRequest,
    TrainRequest,
    ValidationError,
    handle_edit,
    handle_generate,
    handle_train,
    settings_manager,
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
    "/v1/image/flux2/generate",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def generate_flux2_endpoint(
    req: GenerateRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Generate an image from a text prompt (FLUX.2 Klein, text-to-image / img2img).

    Plain text-to-image by default; supply `init_image` (+ optional
    `image_strength`) to run img2img instead — use `/v1/image/flux2/edit` for
    multi-reference editing. The same endpoint serves both `sync` and `async` via
    `mode`. Variant defaults differ: `klein-9b` (default) is distilled and fast
    (few steps, unquantized); `klein-base-4b` / `klein-base-9b` are slower base
    variants (more steps, q8).

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
        spec = model_registry.resolve("flux2", req.model)
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
        type="flux2",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


@router.post(
    "/v1/image/flux2/edit",
    responses=build_job_responses(
        "image/png", "image/jpeg", "image/webp", result_model=ImageResponse
    ),
)
async def edit_flux2_endpoint(
    req: EditRequest,
    accept: str | None = Depends(get_accept),
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Edit / combine one or more reference images with a prompt (FLUX.2 Klein).

    Takes a list of `images` (FileRefs, multi-reference editing) plus a `prompt`;
    `image_strength` controls how much of the input is preserved (lower = closer
    to input). For plain image-to-image from a single seed image, use `init_image`
    on `/v1/image/flux2/generate` instead. The same endpoint serves both `sync`
    and `async` via `mode`.

    Sync content negotiation, transient-model behavior (`loras` / `quantize`
    override), and the ImageResponse `result` shape match
    `/v1/image/flux2/generate`.
    """
    try:
        spec = model_registry.resolve("flux2", req.model)
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
        type="flux2-edit",
        params=req.gen_params() | {"model": spec.name, "mode": req.mode},
        thunk=thunk,
        mode=req.mode,
        accept=accept,
    )


@router.post("/v1/image/flux2/train", responses=build_train_responses())
async def train_flux2_endpoint(
    req: TrainRequest,
    ctx: AppContext = Depends(get_ctx),
    worker: Worker = Depends(get_worker),
) -> Response:
    """Train a LoRA adapter on an image dataset (FLUX.2 Klein base, always async).

    Long-running, so this endpoint is always async: it returns 202 with a
    job_id — poll GET /v1/jobs/{job_id}. Only the base variants
    (`klein-base-4b` default, `klein-base-9b`) are trainable. `training_mode`
    selects the dataset layout: `text` uses captioned images (same-stem `.txt`),
    `edit` uses `*_in.*` / `*_out.*` pairs with `*_in.txt` prompts; the `dataset`
    is a Files-API ZIP. On success the job's `result` holds `adapter_file_id`
    (the trained `.safetensors`, also the artifact), `adapter_bytes`,
    `training_mode`, the resolved `config`, `lora_targets`, `checkpoint`, and
    `timings`; the adapter can then be passed back via `loras` on generate/edit.
    """
    settings = settings_manager.get_settings()

    try:
        spec = model_registry.resolve(
            "flux2", req.model or settings.train_default_model
        )
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc))  # noqa: B904
    if "base" not in spec.name:
        raise HTTPException(
            status_code=400,
            detail="Flux2 training requires klein-base-4b or klein-base-9b",
        )
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
        type="flux2-train",
        params={
            "model": spec.name,
            "dataset": req.dataset.model_dump(mode="json"),
            "training_mode": req.training_mode,
            "num_epochs": req.num_epochs,
            "lora_rank": req.lora_rank,
        },
        thunk=thunk,
        mode="async",
    )


register_capability_endpoints(router, name="flux2", base_path="/v1/image/flux2")
